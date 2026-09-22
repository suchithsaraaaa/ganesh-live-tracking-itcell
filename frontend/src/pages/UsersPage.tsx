import React, { useState, useEffect, useMemo } from 'react';
import {
  Search,
  UserPlus,
  Shield,
  Edit2,
  CheckCircle,
  XCircle,
  AlertCircle,
  Loader2,
  X,
  Filter,
  KeyRound,
} from 'lucide-react';
import {
  fetchUsers,
  createUser,
  updateUser,
  toggleUserActive,
  fetchAuthoritativePoliceStations,
} from '../api/client';
import { User, UserRole, PoliceStationMaster } from '../types';
import { roleLabel } from '../context/AuthContext';
import { LoadingState, EmptyState, ErrorState } from '../components/shared/States';

const CANONICAL_PERMISSIONS = [
  { key: 'view_dashboard', label: 'View Dashboard', desc: 'Access command overview and metrics' },
  { key: 'view_live_map', label: 'View Live Map', desc: 'Track live processions and marker details' },
  { key: 'view_idols', label: 'View Idols', desc: 'Browse and search idol registrations' },
  { key: 'view_journey', label: 'View Journey & Breadcrumbs', desc: 'Historical GPS routes and timestamps' },
  { key: 'manage_assignments', label: 'Manage Assignments', desc: 'Assign constables to GPIDs' },
  { key: 'handover_duty', label: 'Handover Duty', desc: 'Execute duty handovers between officers' },
  { key: 'ingest_telemetry', label: 'Ingest Telemetry', desc: 'Submit live GPS location points' },
  { key: 'generate_reports', label: 'Generate Reports', desc: 'Create and export PDF reports' },
  { key: 'view_audit_logs', label: 'View Audit Logs', desc: 'Review administrative and operational audit trail' },
  { key: 'manage_users', label: 'Manage Users', desc: 'Create, update, and manage officer accounts' },
  { key: 'manage_geography', label: 'Manage Geography', desc: 'Manage station boundaries and geofencing' },
];

export const UsersPage: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [policeStations, setPoliceStations] = useState<PoliceStationMaster[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');

  // Modal states
  const [modalMode, setModalMode] = useState<'create' | 'edit' | null>(null);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Form fields
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    first_name: '',
    last_name: '',
    role: 'CONSTABLE' as UserRole,
    police_id: '',
    police_station: '',
    zone: '',
    division: '',
    is_active: true,
    custom_permissions: [] as string[],
  });

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [userData, psData] = await Promise.all([
        fetchUsers(),
        fetchAuthoritativePoliceStations().catch(() => ({ count: 0, results: [] })),
      ]);
      setUsers(userData.results || []);
      setPoliceStations(psData.results || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load user directory.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const openCreateModal = () => {
    setSelectedUser(null);
    setFormData({
      username: '',
      password: '',
      first_name: '',
      last_name: '',
      role: 'CONSTABLE' as UserRole,
      police_id: '',
      police_station: '',
      zone: '',
      division: '',
      is_active: true,
      custom_permissions: [],
    });
    setFormError(null);
    setModalMode('create');
  };

  const openEditModal = (u: User) => {
    setSelectedUser(u);
    setFormData({
      username: u.username,
      password: '',
      first_name: u.first_name || '',
      last_name: u.last_name || '',
      role: u.role,
      police_id: u.police_id || '',
      police_station: u.police_station || '',
      zone: u.zone || '',
      division: u.division || '',
      is_active: Boolean(u.is_active),
      custom_permissions: Array.isArray(u.custom_permissions) ? u.custom_permissions : [],
    });
    setFormError(null);
    setModalMode('edit');
  };

  const closeModal = () => {
    setModalMode(null);
    setSelectedUser(null);
    setFormError(null);
  };

  const handleStationChange = (stationName: string) => {
    const found = policeStations.find(
      (s) => (s.ps_name || s.name || '').toUpperCase() === stationName.toUpperCase()
    );
    setFormData((prev) => ({
      ...prev,
      police_station: stationName,
      zone: found?.zone || prev.zone,
      division: found?.division || prev.division,
    }));
  };

  const togglePermission = (permKey: string) => {
    setFormData((prev) => {
      const current = prev.custom_permissions;
      if (current.includes(permKey)) {
        return { ...prev, custom_permissions: current.filter((k) => k !== permKey) };
      } else {
        return { ...prev, custom_permissions: [...current, permKey] };
      }
    });
  };

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setFormError(null);

    try {
      if (modalMode === 'create') {
        if (!formData.username.trim()) throw new Error('Username is required.');
        if (!formData.password.trim()) throw new Error('Password is required for new accounts.');

        await createUser({
          username: formData.username.trim(),
          password: formData.password,
          first_name: formData.first_name.trim(),
          last_name: formData.last_name.trim(),
          role: formData.role as UserRole,
          police_id: formData.police_id.trim(),
          police_station: formData.police_station.trim(),
          zone: formData.zone.trim(),
          division: formData.division.trim(),
          is_active: formData.is_active,
          custom_permissions: formData.custom_permissions,
        });
      } else if (modalMode === 'edit' && selectedUser) {
        const payload: any = {
          first_name: formData.first_name.trim(),
          last_name: formData.last_name.trim(),
          role: formData.role as UserRole,
          police_id: formData.police_id.trim(),
          police_station: formData.police_station.trim(),
          zone: formData.zone.trim(),
          division: formData.division.trim(),
          is_active: formData.is_active,
          custom_permissions: formData.custom_permissions,
        };
        if (formData.password.trim()) {
          payload.password = formData.password.trim();
        }
        await updateUser(selectedUser.id, payload);
      }
      closeModal();
      await loadData();
    } catch (err: any) {
      setFormError(err.message || 'Action failed. Please check form values.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleToggleActive = async (u: User) => {
    try {
      await toggleUserActive(u.id);
      setUsers((prev) =>
        prev.map((item) => (item.id === u.id ? { ...item, is_active: !item.is_active } : item))
      );
    } catch (err: any) {
      alert(err.message || 'Failed to toggle active status.');
    }
  };

  const filteredUsers = useMemo(() => {
    const q = search.toLowerCase().trim();
    return users.filter((u) => {
      if (roleFilter !== 'ALL' && u.role !== roleFilter) return false;
      if (statusFilter === 'ACTIVE' && !u.is_active) return false;
      if (statusFilter === 'INACTIVE' && u.is_active) return false;
      if (!q) return true;
      const fullName = `${u.first_name || ''} ${u.last_name || ''}`.toLowerCase();
      const matchName = fullName.includes(q) || u.username.toLowerCase().includes(q);
      const matchPoliceId = (u.police_id || '').toLowerCase().includes(q);
      const matchStation = (u.police_station || '').toLowerCase().includes(q);
      const matchZone = (u.zone || '').toLowerCase().includes(q);
      return matchName || matchPoliceId || matchStation || matchZone;
    });
  }, [users, search, roleFilter, statusFilter]);

  return (
    <div className="h-full flex flex-col overflow-hidden animate-fade-in-up">
      {/* Header */}
      <div className="px-6 pt-6 pb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-lg font-semibold text-text-primary">User Management</h1>
            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-accent/15 text-accent border border-accent/25 mono">
              {users.length} Registered Accounts
            </span>
          </div>
          <p className="text-xs text-text-tertiary mt-0.5">
            Manage police department officer accounts, role hierarchy, jurisdictional boundaries, and security permissions.
          </p>
        </div>

        <button
          onClick={openCreateModal}
          className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-md bg-accent text-base hover:opacity-90 transition-opacity cursor-pointer shrink-0"
        >
          <UserPlus className="w-4 h-4" />
          <span>New User Account</span>
        </button>
      </div>

      {/* Filter Bar */}
      <div className="px-6 pb-4 flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[220px]">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-text-tertiary" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search officer name, username, police ID, or station…"
            className="w-full pl-8 pr-3 py-2 bg-elevated-2 border border-border-default rounded-md text-text-primary text-xs focus:outline-none focus:border-accent"
          />
        </div>

        <div className="relative">
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            aria-label="Filter by Role"
            className="pl-3 pr-8 py-2 bg-elevated-2 border border-border-default rounded-md text-text-primary text-xs focus:outline-none focus:border-accent appearance-none cursor-pointer"
          >
            <option value="ALL">All Roles</option>
            <option value="MAIN_OFFICER">Main Officer / Admin</option>
            <option value="ACP">ACP / Senior Officer</option>
            <option value="SHO">SHO / Station Officer</option>
            <option value="CONSTABLE">Constable / Ground Staff</option>
          </select>
          <Filter className="w-3 h-3 absolute right-2.5 top-1/2 -translate-y-1/2 text-text-tertiary pointer-events-none" />
        </div>

        <div className="relative">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            aria-label="Filter by Status"
            className="pl-3 pr-8 py-2 bg-elevated-2 border border-border-default rounded-md text-text-primary text-xs focus:outline-none focus:border-accent appearance-none cursor-pointer"
          >
            <option value="ALL">All Status</option>
            <option value="ACTIVE">Active Only</option>
            <option value="INACTIVE">Disabled Only</option>
          </select>
          <Filter className="w-3 h-3 absolute right-2.5 top-1/2 -translate-y-1/2 text-text-tertiary pointer-events-none" />
        </div>
      </div>

      {/* Users Table */}
      <div className="flex-1 overflow-y-auto px-6 pb-6">
        {loading && <LoadingState label="Loading officer accounts…" />}
        {!loading && error && <ErrorState message={error} onRetry={loadData} />}
        {!loading && !error && filteredUsers.length === 0 && (
          <EmptyState title="No matching user accounts found" hint="Try adjusting your role or search filters." />
        )}
        {!loading && !error && filteredUsers.length > 0 && (
          <div className="bg-elevated border border-border-subtle rounded-lg overflow-hidden">
            <div className="flex items-center gap-3 px-4 py-2.5 text-[10px] font-medium uppercase tracking-wider text-text-tertiary border-b border-border-subtle">
              <span className="w-48">Officer / Username</span>
              <span className="w-28">Police ID</span>
              <span className="w-36">Role</span>
              <span className="w-44">Police Station / Zone</span>
              <span className="w-32">Effective Rights</span>
              <span className="w-24">Status</span>
              <span className="w-28 text-right">Actions</span>
            </div>

            <div className="divide-y divide-border-subtle">
              {filteredUsers.map((u) => {
                const fullName = `${u.first_name || ''} ${u.last_name || ''}`.trim() || u.username;
                const hasCustomPerms = Array.isArray(u.custom_permissions) && u.custom_permissions.length > 0;
                return (
                  <div key={u.id} className="flex items-center gap-3 px-4 py-3 text-xs hover:bg-elevated-2/50 transition-colors">
                    {/* User name & username */}
                    <div className="w-48 min-w-0">
                      <div className="font-semibold text-text-primary truncate">{fullName}</div>
                      <div className="text-[11px] text-text-tertiary mono truncate">@{u.username}</div>
                    </div>

                    {/* Police ID */}
                    <div className="w-28">
                      {u.police_id ? (
                        <span className="mono text-[11px] text-text-secondary bg-elevated-2 px-1.5 py-0.5 rounded border border-border-subtle">
                          {u.police_id}
                        </span>
                      ) : (
                        <span className="text-text-tertiary text-[11px]">—</span>
                      )}
                    </div>

                    {/* Role */}
                    <div className="w-36">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold border ${
                          u.role === 'MAIN_OFFICER'
                            ? 'bg-accent/15 text-accent border-accent/30'
                            : u.role === 'ACP'
                            ? 'bg-status-active/15 text-status-active border-status-active/30'
                            : u.role === 'SHO'
                            ? 'bg-status-holding/15 text-status-holding border-status-holding/30'
                            : 'bg-elevated-2 text-text-secondary border-border-default'
                        }`}
                      >
                        {roleLabel(u.role)}
                      </span>
                    </div>

                    {/* Jurisdiction */}
                    <div className="w-44 min-w-0">
                      <div className="text-text-primary truncate font-medium">
                        {u.police_station || 'City Wide'}
                      </div>
                      <div className="text-[10px] text-text-tertiary truncate">
                        {u.zone || 'Hyderabad District'}
                      </div>
                    </div>

                    {/* Permissions summary */}
                    <div className="w-32">
                      {hasCustomPerms ? (
                        <span className="text-[10px] font-medium text-accent bg-accent/10 px-1.5 py-0.5 rounded border border-accent/20">
                          {u.custom_permissions!.length} custom
                        </span>
                      ) : (
                        <span className="text-[10px] text-text-tertiary">Role defaults</span>
                      )}
                    </div>

                    {/* Status */}
                    <div className="w-24">
                      <span
                        className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium ${
                          u.is_active
                            ? 'bg-status-active-soft text-status-active'
                            : 'bg-status-critical-soft text-status-critical'
                        }`}
                      >
                        {u.is_active ? 'Active' : 'Disabled'}
                      </span>
                    </div>

                    {/* Actions */}
                    <div className="w-28 flex items-center justify-end space-x-1.5">
                      <button
                        onClick={() => openEditModal(u)}
                        title="Edit Officer & Permissions"
                        className="p-1.5 rounded hover:bg-elevated-2 text-text-tertiary hover:text-text-primary transition-colors cursor-pointer"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleToggleActive(u)}
                        title={u.is_active ? 'Disable Account' : 'Enable Account'}
                        className={`p-1.5 rounded hover:bg-elevated-2 transition-colors cursor-pointer ${
                          u.is_active
                            ? 'text-status-critical hover:text-status-critical'
                            : 'text-status-active hover:text-status-active'
                        }`}
                      >
                        {u.is_active ? <XCircle className="w-3.5 h-3.5" /> : <CheckCircle className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Create / Edit Modal */}
      {modalMode && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-xl bg-elevated border border-border-default rounded-lg shadow-2xl overflow-hidden flex flex-col max-h-[92vh]">
            {/* Modal Header */}
            <div className="px-5 py-3.5 bg-base border-b border-border-subtle flex items-center justify-between shrink-0">
              <div className="flex items-center space-x-2">
                <Shield className="w-5 h-5 text-accent" />
                <h2 className="text-sm font-semibold text-text-primary uppercase tracking-wider">
                  {modalMode === 'create' ? 'Create Officer Account' : `Edit Account: @${selectedUser?.username}`}
                </h2>
              </div>
              <button
                onClick={closeModal}
                className="text-text-tertiary hover:text-text-primary transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <form onSubmit={handleFormSubmit} className="p-5 space-y-4 text-xs overflow-y-auto flex-1">
              {formError && (
                <div className="p-3 bg-status-critical-soft border border-status-critical/30 rounded-md flex items-start space-x-2 text-status-critical text-xs">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                  <span>{formError}</span>
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-text-secondary font-medium mb-1">
                    Username <span className="text-status-critical">*</span>
                  </label>
                  <input
                    type="text"
                    value={formData.username}
                    onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                    disabled={modalMode === 'edit'}
                    required
                    placeholder="e.g. cmnr_sho_01"
                    className="w-full px-3 py-2 bg-elevated-2 border border-border-default rounded-md text-text-primary text-xs focus:outline-none focus:border-accent disabled:opacity-60 mono"
                  />
                </div>

                <div>
                  <label className="block text-text-secondary font-medium mb-1">
                    {modalMode === 'create' ? 'Password *' : 'Reset Password (optional)'}
                  </label>
                  <input
                    type="password"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    required={modalMode === 'create'}
                    placeholder={modalMode === 'create' ? 'Enter secure password' : 'Leave blank to keep current'}
                    className="w-full px-3 py-2 bg-elevated-2 border border-border-default rounded-md text-text-primary text-xs focus:outline-none focus:border-accent"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-text-secondary font-medium mb-1">First Name</label>
                  <input
                    type="text"
                    value={formData.first_name}
                    onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                    placeholder="e.g. Rajesh"
                    className="w-full px-3 py-2 bg-elevated-2 border border-border-default rounded-md text-text-primary text-xs focus:outline-none focus:border-accent"
                  />
                </div>

                <div>
                  <label className="block text-text-secondary font-medium mb-1">Last Name</label>
                  <input
                    type="text"
                    value={formData.last_name}
                    onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                    placeholder="e.g. Kumar"
                    className="w-full px-3 py-2 bg-elevated-2 border border-border-default rounded-md text-text-primary text-xs focus:outline-none focus:border-accent"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-text-secondary font-medium mb-1">
                    Operational Role <span className="text-status-critical">*</span>
                  </label>
                  <select
                    value={formData.role}
                    onChange={(e) => setFormData({ ...formData, role: e.target.value as UserRole })}
                    className="w-full px-3 py-2 bg-elevated-2 border border-border-default rounded-md text-text-primary text-xs focus:outline-none focus:border-accent cursor-pointer"
                  >
                    <option value="CONSTABLE">CONSTABLE (Ground Staff)</option>
                    <option value="SHO">SHO (Station Officer)</option>
                    <option value="ACP">ACP (Senior Officer)</option>
                    <option value="MAIN_OFFICER">MAIN_OFFICER (System Admin)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-text-secondary font-medium mb-1">Police ID / Badge No</label>
                  <input
                    type="text"
                    value={formData.police_id}
                    onChange={(e) => setFormData({ ...formData, police_id: e.target.value })}
                    placeholder="e.g. PC-7489"
                    className="w-full px-3 py-2 bg-elevated-2 border border-border-default rounded-md text-text-primary text-xs focus:outline-none focus:border-accent mono"
                  />
                </div>
              </div>

              {/* Jurisdiction */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-text-secondary font-medium mb-1">Police Station</label>
                  {policeStations.length > 0 ? (
                    <select
                      value={formData.police_station}
                      onChange={(e) => handleStationChange(e.target.value)}
                      className="w-full px-3 py-2 bg-elevated-2 border border-border-default rounded-md text-text-primary text-xs focus:outline-none focus:border-accent cursor-pointer"
                    >
                      <option value="">None / City Wide</option>
                      {policeStations.map((s) => {
                        const sName = s.ps_name || s.name || '';
                        const sCode = s.ps_code || s.code || '';
                        return (
                          <option key={s.id} value={sName}>
                            {sName} {sCode ? `(${sCode})` : ''}
                          </option>
                        );
                      })}
                    </select>
                  ) : (
                    <input
                      type="text"
                      value={formData.police_station}
                      onChange={(e) => setFormData({ ...formData, police_station: e.target.value })}
                      placeholder="e.g. CHARMINAR"
                      className="w-full px-3 py-2 bg-elevated-2 border border-border-default rounded-md text-text-primary text-xs focus:outline-none focus:border-accent"
                    />
                  )}
                </div>

                <div>
                  <label className="block text-text-secondary font-medium mb-1">Zone</label>
                  <input
                    type="text"
                    value={formData.zone}
                    onChange={(e) => setFormData({ ...formData, zone: e.target.value })}
                    placeholder="e.g. SOUTH ZONE"
                    className="w-full px-3 py-2 bg-elevated-2 border border-border-default rounded-md text-text-primary text-xs focus:outline-none focus:border-accent"
                  />
                </div>
              </div>

              {/* Status */}
              <div className="pt-1">
                <label className="flex items-center space-x-2 text-text-secondary cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={formData.is_active}
                    onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                    className="rounded border-border-default bg-elevated-2 text-status-active focus:ring-0"
                  />
                  <span className="font-medium">Account is Active and authorized to log in</span>
                </label>
              </div>

              {/* Granular Permissions Section */}
              <div className="pt-2 border-t border-border-subtle">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-1.5">
                    <KeyRound className="w-3.5 h-3.5 text-accent" />
                    <span className="font-semibold text-text-primary uppercase tracking-wider text-[11px]">
                      Granular Capabilities & Permissions
                    </span>
                  </div>
                  <span className="text-[10px] text-text-tertiary">
                    Leave empty to inherit standard role defaults
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 bg-base p-3 rounded-md border border-border-subtle max-h-48 overflow-y-auto">
                  {CANONICAL_PERMISSIONS.map((perm) => {
                    const isChecked = formData.custom_permissions.includes(perm.key);
                    return (
                      <label
                        key={perm.key}
                        onClick={() => togglePermission(perm.key)}
                        className={`flex items-start space-x-2 p-2 rounded cursor-pointer transition-colors ${
                          isChecked ? 'bg-accent/10 border border-accent/25' : 'hover:bg-elevated border border-transparent'
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => {}}
                          className="mt-0.5 rounded border-border-default bg-elevated-2 text-accent focus:ring-0 shrink-0"
                        />
                        <div className="min-w-0">
                          <div className="font-medium text-text-primary text-[11px] truncate">{perm.label}</div>
                          <div className="text-[9px] text-text-tertiary truncate">{perm.desc}</div>
                        </div>
                      </label>
                    );
                  })}
                </div>
              </div>

              {/* Submit Buttons */}
              <div className="pt-3 border-t border-border-subtle flex items-center justify-end space-x-3 shrink-0">
                <button
                  type="button"
                  onClick={closeModal}
                  className="px-4 py-2 rounded-md border border-border-default text-text-secondary hover:text-text-primary hover:bg-elevated-2 transition-colors cursor-pointer text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 bg-accent hover:opacity-90 disabled:opacity-50 text-base font-semibold rounded-md transition-opacity cursor-pointer text-xs flex items-center space-x-1.5"
                >
                  {submitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  <span>{modalMode === 'create' ? 'Create Account' : 'Save Changes'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
