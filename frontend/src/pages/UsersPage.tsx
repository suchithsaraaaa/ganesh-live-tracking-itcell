import React, { useState, useEffect, useMemo } from 'react';
import {
  Search,
  UserPlus,
  Edit2,
  CheckCircle,
  XCircle,
  AlertCircle,
  Loader2,
  X,
  KeyRound,
  Trash2,
  Eye,
  EyeOff,
  RotateCcw,
} from 'lucide-react';
import {
  fetchUsers,
  createUser,
  updateUser,
  toggleUserActive,
  deleteUser,
  fetchAuthoritativePoliceStations,
  fetchAuthoritativeZones,
} from '../api/client';
import { User, UserRole, PoliceStationMaster } from '../types';
import { useAuth, roleLabel, isSuperAdmin } from '../context/AuthContext';
import { LoadingState, EmptyState, ErrorState } from '../components/shared/States';
import telanganaPoliceLogo from '../assets/branding/telangana-police-logo.png';

const CANONICAL_PERMISSIONS = [
  // Dashboard
  { key: 'view_dashboard', label: 'View Dashboard', desc: 'Access command overview, metrics, and procession cards', category: 'Dashboard' },

  // Idols
  { key: 'view_idols', label: 'View Idols', desc: 'Browse and search registered Ganesh idols', category: 'Idols' },
  { key: 'view_gpids', label: 'View GPIDs', desc: 'Authoritative idol identifiers and references', category: 'Idols' },
  { key: 'view_police_stations', label: 'View Police Stations', desc: 'Inspect police stations and boundary maps', category: 'Idols' },
  { key: 'view_holding_points', label: 'View Holding Points', desc: 'Inspect holding buffers and queue management points', category: 'Idols' },
  { key: 'view_visarjan_points', label: 'View Visarjan Points', desc: 'Inspect water body immersion locations and tanks', category: 'Idols' },

  // Live Operations
  { key: 'view_live_map', label: 'View Live Map', desc: 'Track live processions and marker telemetry', category: 'Live Operations' },
  { key: 'view_processions', label: 'View Processions', desc: 'Monitor active procession movements and states', category: 'Live Operations' },
  { key: 'view_journey', label: 'View Journey & Breadcrumbs', desc: 'Historical GPS routes and timestamps', category: 'Live Operations' },
  { key: 'view_tracking_history', label: 'View Tracking History', desc: 'Detailed GPS session logs and point records', category: 'Live Operations' },
  { key: 'ingest_telemetry', label: 'Ingest Telemetry', desc: 'Transmit and ingest live GPS location points', category: 'Live Operations' },
  { key: 'view_officer_locations', label: 'View Officer Locations', desc: 'View field officer coordinates and live telemetry', category: 'Live Operations' },

  // Assignments
  { key: 'view_assignments', label: 'View Assignments', desc: 'Oversight of officer duties and pairings', category: 'Assignments' },
  { key: 'assign_field_officers', label: 'Assign Field Officers', desc: 'Pair constables with operational idols', category: 'Assignments' },
  { key: 'create_assignments', label: 'Create Assignments', desc: 'Initiate new duty assignments', category: 'Assignments' },
  { key: 'reassign_assignments', label: 'Reassign Officers', desc: 'Transfer duties to alternative officers', category: 'Assignments' },
  { key: 'manage_assignments', label: 'Manage Assignments', desc: 'Complete assignment lifecycle management', category: 'Assignments' },
  { key: 'handover_duty', label: 'Handover Duty', desc: 'Execute duty handovers between officers', category: 'Assignments' },

  // Reports
  { key: 'view_reports', label: 'View Reports', desc: 'Browse generated operational PDF reports', category: 'Reports' },
  { key: 'generate_reports', label: 'Generate Reports', desc: 'Create and export PDF reports', category: 'Reports' },
  { key: 'export_reports', label: 'Export Reports', desc: 'Download CSV and PDF data exports', category: 'Reports' },

  // System & Audits
  { key: 'view_audit_logs', label: 'View Audit Logs', desc: 'Review administrative and operational audit trail', category: 'System & Audits' },
  { key: 'view_alerts', label: 'View Alerts', desc: 'Receive geofence and stoppage alerts', category: 'System & Audits' },
  { key: 'manage_geography', label: 'Manage Geography', desc: 'Manage station boundaries and geofencing', category: 'System & Audits' },

  // User & Role Management
  { key: 'manage_users', label: 'Manage Users', desc: 'Create, update, and manage officer accounts', category: 'User Management' },
  { key: 'manage_permissions', label: 'Manage Permissions', desc: 'Assign granular user capability overrides', category: 'User Management' },
  { key: 'manage_roles', label: 'Manage Roles', desc: 'Assign and upgrade user operational roles', category: 'Role Management' },
  { key: 'manage_role_templates', label: 'Manage Role Templates', desc: 'Global role default capabilities configuration', category: 'Role Management' },
];

export const UsersPage: React.FC = () => {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [totalRegisteredCount, setTotalRegisteredCount] = useState<number>(0);

  const [policeStations, setPoliceStations] = useState<PoliceStationMaster[]>([]);
  const [zones, setZones] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Check if current user is a zone-scoped administrator
  const isZonedAdmin = useMemo(() => {
    return !!(
      currentUser?.zone &&
      !(currentUser as any).is_superuser &&
      (currentUser.role === 'MAIN_OFFICER' || (currentUser.role as any) === 'SYS_ADMIN' || currentUser.role === 'ACP')
    );
  }, [currentUser]);

  // Filters (Backend-driven)
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [selectedZone, setSelectedZone] = useState(() => {
    if (currentUser?.zone && !(currentUser as any).is_superuser) {
      return currentUser.zone;
    }
    return 'All Zones';
  });
  const [selectedStation, setSelectedStation] = useState('All Police Stations');
  const [roleFilter, setRoleFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');

  // Keep selectedZone synchronized when current user loads
  useEffect(() => {
    if (isZonedAdmin && currentUser?.zone && selectedZone !== currentUser.zone) {
      setSelectedZone(currentUser.zone);
    }
  }, [isZonedAdmin, currentUser?.zone]);

  // Password visibility in modal
  const [showPassword, setShowPassword] = useState(false);

  // Modal states
  const [modalMode, setModalMode] = useState<'create' | 'edit' | null>(null);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const isEditingSelf = useMemo(() => {
    return Boolean(
      modalMode === 'edit' &&
      selectedUser &&
      currentUser &&
      (selectedUser.id === currentUser.id || selectedUser.username === currentUser.username)
    );
  }, [modalMode, selectedUser, currentUser]);

  // Delete confirmation modal
  const [deleteTarget, setDeleteTarget] = useState<User | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

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

  // Debounce search input by 250ms
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(search);
    }, 250);
    return () => clearTimeout(handler);
  }, [search]);

  // Load master zones & stations once on mount
  useEffect(() => {
    async function loadMasterData() {
      try {
        const [psData, zonesData] = await Promise.all([
          fetchAuthoritativePoliceStations().catch(() => ({ count: 0, results: [] })),
          fetchAuthoritativeZones().catch(() => []),
        ]);
        setPoliceStations(psData.results || []);
        setZones(zonesData || []);
      } catch (err: any) {
        console.error('Failed to load master zones/stations', err);
      }
    }
    loadMasterData();
  }, []);

  // Compute available zones
  const availableZones = useMemo(() => {
    if (isZonedAdmin && currentUser?.zone) {
      return [currentUser.zone];
    }
    if (zones && zones.length > 0) return zones;
    const zSet = new Set<string>();
    policeStations.forEach((ps) => {
      if (ps.zone) zSet.add(ps.zone);
    });
    return Array.from(zSet).sort();
  }, [isZonedAdmin, currentUser?.zone, zones, policeStations]);

  // Compute cascading police stations based on selectedZone
  const availableStations = useMemo(() => {
    if (!selectedZone || selectedZone === 'All Zones') {
      return Array.from(new Set(policeStations.map((ps) => ps.ps_name))).sort();
    }
    const cleanSelected = selectedZone.replace(/\s+/g, '').toLowerCase();
    return Array.from(
      new Set(
        policeStations
          .filter((ps) => (ps.zone || '').replace(/\s+/g, '').toLowerCase() === cleanSelected)
          .map((ps) => ps.ps_name)
      )
    ).sort();
  }, [policeStations, selectedZone]);

  // Handle Zone filter change with cascading station reset
  const handleZoneFilterChange = (zone: string) => {
    setSelectedZone(zone);
    if (selectedStation !== 'All Police Stations') {
      if (zone !== 'All Zones') {
        const cleanZone = zone.replace(/\s+/g, '').toLowerCase();
        const belongs = policeStations.some(
          (ps) =>
            (ps.zone || '').replace(/\s+/g, '').toLowerCase() === cleanZone &&
            (ps.ps_name || '').trim().toLowerCase() === selectedStation.trim().toLowerCase()
        );
        if (!belongs) {
          setSelectedStation('All Police Stations');
        }
      }
    }
  };

  const isFiltered = useMemo(() => {
    return (
      search.trim() !== '' ||
      selectedZone !== 'All Zones' ||
      selectedStation !== 'All Police Stations' ||
      roleFilter !== 'ALL' ||
      statusFilter !== 'ALL'
    );
  }, [search, selectedZone, selectedStation, roleFilter, statusFilter]);

  const handleClearFilters = () => {
    setSearch('');
    setDebouncedSearch('');
    setSelectedZone(isZonedAdmin && currentUser?.zone ? currentUser.zone : 'All Zones');
    setSelectedStation('All Police Stations');
    setRoleFilter('ALL');
    setStatusFilter('ALL');
  };

  // Load users from backend API using database filtering
  const loadUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Parameters<typeof fetchUsers>[0] = {};
      if (debouncedSearch.trim()) params.search = debouncedSearch.trim();
      if (selectedZone !== 'All Zones') params.zone = selectedZone;
      if (selectedStation !== 'All Police Stations') params.police_station = selectedStation;
      if (roleFilter !== 'ALL') params.role = roleFilter;
      if (statusFilter === 'ACTIVE') params.status = 'active';
      if (statusFilter === 'INACTIVE') params.status = 'inactive';

      const userData = await fetchUsers(params);
      setUsers(userData.results || []);
      if (userData.total_count !== undefined) {
        setTotalRegisteredCount(userData.total_count);
      } else if (!isFiltered) {
        setTotalRegisteredCount(userData.count || (userData.results ? userData.results.length : 0));
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load user directory.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, [debouncedSearch, selectedZone, selectedStation, roleFilter, statusFilter]);

  const openCreateModal = () => {
    setSelectedUser(null);
    setShowPassword(false);
    setFormData({
      username: '',
      password: '',
      first_name: '',
      last_name: '',
      role: 'CONSTABLE' as UserRole,
      police_id: '',
      police_station: '',
      zone: isZonedAdmin && currentUser?.zone ? currentUser.zone : '',
      division: '',
      is_active: true,
      custom_permissions: [],
    });
    setFormError(null);
    setModalMode('create');
  };

  const openEditModal = (u: User) => {
    setSelectedUser(u);
    setShowPassword(false);
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
    setShowPassword(false);
    setFormError(null);
  };

  const filteredStationsForForm = useMemo(() => {
    if (!formData.zone) return [];
    return policeStations.filter(
      (s) => (s.zone || '').trim().toUpperCase() === formData.zone.trim().toUpperCase()
    );
  }, [policeStations, formData.zone]);

  const handleZoneChange = (zone: string) => {
    setFormData((prev) => ({
      ...prev,
      zone: zone,
      police_station: '',
      division: '',
    }));
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
      if (formData.role === 'CONSTABLE') {
        if (!formData.zone.trim()) throw new Error('Zone is required for Constable accounts.');
        if (!formData.police_station.trim()) throw new Error('Police Station is required for Constable accounts.');
      } else if (formData.role === 'SHO') {
        if (!formData.zone.trim()) throw new Error('Zone is required for SHO accounts.');
        if (!formData.police_station.trim()) throw new Error('Police Station is required for SHO accounts.');
      } else if (formData.role === 'ACP') {
        if (!formData.zone.trim()) throw new Error('Zone is required for ACP accounts.');
      }

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
      await loadUsers();
    } catch (err: any) {
      setFormError(err.message || 'Action failed. Please check form values.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleToggleActive = async (u: User) => {
    try {
      await toggleUserActive(u.id);
      await loadUsers();
    } catch (err: any) {
      alert(err.message || 'Failed to toggle active status.');
    }
  };

  const openDeleteModal = (u: User) => {
    setDeleteTarget(u);
    setDeleteError(null);
  };

  const closeDeleteModal = () => {
    setDeleteTarget(null);
    setDeleteError(null);
    setDeleting(false);
  };

  const handleDeleteUser = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await deleteUser(deleteTarget.id);
      closeDeleteModal();
      await loadUsers();
    } catch (err: any) {
      setDeleteError(err.message || 'Deletion failed. Please try again.');
      setDeleting(false);
    }
  };

  return (
    <div className="h-full flex flex-col overflow-hidden animate-fade-in-up">
      {/* Header */}
      <div className="px-6 pt-6 pb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-start gap-3.5">
          <img
            src={telanganaPoliceLogo}
            alt="Telangana State Police"
            className="w-9 h-11 object-contain shrink-0 mt-0.5"
          />
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-lg font-semibold text-text-primary">User Management</h1>
              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-accent/15 text-accent border border-accent/25 mono">
                {totalRegisteredCount} Registered Accounts
              </span>
              {isFiltered && (
                <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-elevated-2 text-text-secondary border border-border-default mono">
                  Showing {users.length} of {totalRegisteredCount} accounts
                </span>
              )}
            </div>
            <p className="text-xs text-text-tertiary mt-0.5">
              Manage police department officer accounts, role hierarchy, jurisdictional boundaries, and security permissions.
            </p>
          </div>
        </div>

        <button
          onClick={openCreateModal}
          className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-md bg-accent text-base hover:opacity-90 transition-opacity cursor-pointer shrink-0"
        >
          <UserPlus className="w-4 h-4" />
          <span>New User Account</span>
        </button>
      </div>

      {/* Filter / Control Bar */}
      <div className="px-6 py-3 bg-base border-b border-border-subtle shrink-0">
        <div className="space-y-2.5">
          {/* Row 1: Search & Zone */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5 items-end">
            <div className="md:col-span-2">
              <label className="block text-[10px] uppercase font-bold text-text-tertiary mb-1">
                Search Officers
              </label>
              <div className="relative">
                <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-text-tertiary" />
                <input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search name, username, police ID, PS…"
                  className="w-full pl-8 pr-3 py-1.5 bg-elevated border border-border-default rounded text-xs text-text-primary focus:outline-none focus:border-accent"
                />
              </div>
            </div>

            <div>
              <label className="block text-[10px] uppercase font-bold text-text-tertiary mb-1">
                Zone
              </label>
              <select
                value={selectedZone}
                onChange={(e) => handleZoneFilterChange(e.target.value)}
                disabled={isZonedAdmin}
                className="w-full px-2.5 py-1.5 bg-elevated border border-border-default rounded text-xs text-text-primary focus:outline-none focus:border-accent cursor-pointer disabled:opacity-60"
              >
                {!isZonedAdmin && <option value="All Zones">All Zones</option>}
                {availableZones.map((z) => (
                  <option key={z} value={z}>
                    {z}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Row 2: Police Station, Officer Level / Role, Status, Clear Filters */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2.5 items-end">
            {/* Police Station Filter (Cascading) */}
            <div>
              <label className="block text-[10px] uppercase font-bold text-text-tertiary mb-1">
                Police Station
              </label>
              <select
                value={selectedStation}
                onChange={(e) => setSelectedStation(e.target.value)}
                className="w-full px-2.5 py-1.5 bg-elevated border border-border-default rounded text-xs text-text-primary focus:outline-none focus:border-accent cursor-pointer"
              >
                <option value="All Police Stations">All Police Stations</option>
                {availableStations.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>

            {/* Officer Level / Role Filter */}
            <div>
              <label className="block text-[10px] uppercase font-bold text-text-tertiary mb-1">
                Officer Level / Role
              </label>
              <select
                value={roleFilter}
                onChange={(e) => setRoleFilter(e.target.value)}
                aria-label="Filter by Officer Level"
                className="w-full px-2.5 py-1.5 bg-elevated border border-border-default rounded text-xs text-text-primary focus:outline-none focus:border-accent cursor-pointer"
              >
                <option value="ALL">All Roles / Levels</option>
                <option value="SUPER_ADMIN">Super Administrator</option>
                <option value="MAIN_OFFICER">Main Officer / Admin</option>
                <option value="SYS_ADMIN">Zonal System Admin</option>
                <option value="ACP">ACP / Senior Officer</option>
                <option value="SHO">SHO / Station Officer</option>
                <option value="CONSTABLE">Constable / Ground Staff</option>
              </select>
            </div>

            {/* Status Filter */}
            <div>
              <label className="block text-[10px] uppercase font-bold text-text-tertiary mb-1">
                Status
              </label>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                aria-label="Filter by Status"
                className="w-full px-2.5 py-1.5 bg-elevated border border-border-default rounded text-xs text-text-primary focus:outline-none focus:border-accent cursor-pointer"
              >
                <option value="ALL">All Status</option>
                <option value="ACTIVE">Active Only</option>
                <option value="INACTIVE">Disabled Only</option>
              </select>
            </div>

            {/* Clear Filters Button */}
            <div>
              <button
                type="button"
                onClick={handleClearFilters}
                disabled={!isFiltered}
                className={`w-full py-1.5 px-3 rounded text-xs font-semibold border flex items-center justify-center gap-1.5 transition-colors cursor-pointer ${
                  isFiltered
                    ? 'bg-accent/15 border-accent/40 text-accent hover:bg-accent/25'
                    : 'bg-elevated/40 border-border-subtle text-text-tertiary cursor-not-allowed opacity-40'
                }`}
                title="Reset all filters to default"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Clear Filters</span>
              </button>
            </div>
          </div>
        </div>

        {/* Active Filter Badges */}
        {isFiltered && (
          <div className="flex flex-wrap items-center gap-2 mt-2 pt-2 border-t border-border-subtle/50 text-xs">
            <span className="text-[11px] text-text-tertiary font-medium">Active filters:</span>
            {selectedZone !== 'All Zones' && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] bg-accent/10 text-accent border border-accent/20">
                Zone: {selectedZone}
                <button onClick={() => setSelectedZone('All Zones')} className="hover:text-white"><X className="w-2.5 h-2.5" /></button>
              </span>
            )}
            {selectedStation !== 'All Police Stations' && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] bg-accent/10 text-accent border border-accent/20">
                PS: {selectedStation}
                <button onClick={() => setSelectedStation('All Police Stations')} className="hover:text-white"><X className="w-2.5 h-2.5" /></button>
              </span>
            )}
            {roleFilter !== 'ALL' && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] bg-accent/10 text-accent border border-accent/20">
                Level: {roleLabel(roleFilter as UserRole)}
                <button onClick={() => setRoleFilter('ALL')} className="hover:text-white"><X className="w-2.5 h-2.5" /></button>
              </span>
            )}
            {statusFilter !== 'ALL' && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] bg-accent/10 text-accent border border-accent/20">
                Status: {statusFilter === 'ACTIVE' ? 'Active' : 'Disabled'}
                <button onClick={() => setStatusFilter('ALL')} className="hover:text-white"><X className="w-2.5 h-2.5" /></button>
              </span>
            )}
            {debouncedSearch && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] bg-accent/10 text-accent border border-accent/20">
                Search: "{debouncedSearch}"
                <button onClick={() => setSearch('')} className="hover:text-white"><X className="w-2.5 h-2.5" /></button>
              </span>
            )}
            <button
              onClick={handleClearFilters}
              className="text-[11px] text-accent hover:underline ml-auto cursor-pointer flex items-center gap-1"
            >
              <RotateCcw className="w-3 h-3" />
              <span>Clear Filters</span>
            </button>
          </div>
        )}
      </div>

      {/* Users Table */}
      <div className="flex-1 overflow-y-auto px-6 pb-6">
        {loading && <LoadingState label="Loading officer accounts…" />}
        {!loading && error && <ErrorState message={error} onRetry={loadUsers} />}
        {!loading && !error && users.length === 0 && (
          <EmptyState title="No matching user accounts found" hint="Try adjusting your role, zone, station, or search filters." />
        )}
        {!loading && !error && users.length > 0 && (
          <div className="bg-elevated border border-border-subtle rounded-lg overflow-hidden">
            <div className="flex items-center gap-3 px-4 py-2.5 text-[10px] font-medium uppercase tracking-wider text-text-tertiary border-b border-border-subtle">
              <span className="w-48">Officer / Username</span>
              <span className="w-28">Police ID</span>
              <span className="w-36">Role</span>
              <span className="w-44">Police Station / Zone</span>
              <span className="w-32">Effective Rights</span>
              <span className="w-24">Status</span>
              <span className="w-36 text-right">Actions</span>
            </div>

            <div className="divide-y divide-border-subtle">
              {users.map((u) => {
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
                          u.role === 'SUPER_ADMIN'
                            ? 'bg-amber-500/20 text-amber-300 border-amber-500/40 font-bold'
                            : u.role === 'MAIN_OFFICER'
                            ? 'bg-accent/15 text-accent border-accent/30'
                            : (u.role as string) === 'SYS_ADMIN'
                            ? 'bg-indigo-500/15 text-indigo-300 border-indigo-500/30'
                            : u.role === 'ACP'
                            ? 'bg-status-active/15 text-status-active border-status-active/30'
                            : u.role === 'SHO'
                            ? 'bg-status-holding/15 text-status-holding border-status-holding/30'
                            : 'bg-elevated-2 text-text-secondary border-border-default'
                        }`}
                      >
                        {roleLabel(u.role, u)}
                      </span>
                    </div>

                    {/* Jurisdiction */}
                    <div className="w-44 min-w-0">
                      <div className="text-text-primary truncate font-medium">
                        {u.police_station || (u.role === 'SYS_ADMIN' && u.zone ? `${u.zone} (Zone Wide)` : (u.role === 'SUPER_ADMIN' || u.role === 'MAIN_OFFICER') && !u.zone ? 'City Wide' : u.zone || 'City Wide')}
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
                    <div className="w-36 flex items-center justify-end space-x-1">
                      {(() => {
                        const isSelf = currentUser?.id === u.id || currentUser?.username === u.username;
                        const isTargetSuper = u.role === 'SUPER_ADMIN';
                        const callerIsSuper = isSuperAdmin(currentUser);
                        const canEditTarget = callerIsSuper || (
                          currentUser?.role === 'MAIN_OFFICER' ? !isTargetSuper :
                          currentUser?.role === 'SYS_ADMIN' ? (isSelf || u.role === 'CONSTABLE' || u.role === 'SHO') :
                          false
                        );
                        const canManageTarget = callerIsSuper || (
                          currentUser?.role === 'MAIN_OFFICER' ? !isTargetSuper :
                          currentUser?.role === 'SYS_ADMIN' ? (u.role === 'CONSTABLE' || u.role === 'SHO') :
                          false
                        );

                        return (
                          <>
                            <button
                              onClick={() => canEditTarget && openEditModal(u)}
                              disabled={!canEditTarget}
                              title={!canEditTarget ? "You do not have permission to edit this account." : "Edit Officer & Permissions"}
                              className={`p-1.5 rounded transition-colors ${
                                !canEditTarget
                                  ? 'opacity-30 cursor-not-allowed text-text-tertiary'
                                  : 'hover:bg-elevated-2 text-text-tertiary hover:text-text-primary cursor-pointer'
                              }`}
                            >
                              <Edit2 className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => canManageTarget && !isSelf && handleToggleActive(u)}
                              disabled={!canManageTarget || isSelf}
                              title={
                                isSelf
                                  ? "Cannot disable your own administrative account."
                                  : !canManageTarget
                                  ? "You do not have permission to disable this account."
                                  : u.is_active
                                  ? 'Disable Account'
                                  : 'Enable Account'
                              }
                              className={`p-1.5 rounded transition-colors ${
                                !canManageTarget || isSelf
                                  ? 'opacity-30 cursor-not-allowed text-text-tertiary'
                                  : u.is_active
                                  ? 'hover:bg-elevated-2 text-status-critical hover:text-status-critical cursor-pointer'
                                  : 'hover:bg-elevated-2 text-status-active hover:text-status-active cursor-pointer'
                              }`}
                            >
                              {u.is_active ? <XCircle className="w-3.5 h-3.5" /> : <CheckCircle className="w-3.5 h-3.5" />}
                            </button>
                            <button
                              onClick={() => canManageTarget && !isSelf && openDeleteModal(u)}
                              disabled={!canManageTarget || isSelf}
                              title={
                                isSelf
                                  ? "You cannot delete your own account."
                                  : !canManageTarget
                                  ? "You do not have permission to delete this account."
                                  : "Permanently Delete Account"
                              }
                              className={`p-1.5 rounded transition-colors ${
                                !canManageTarget || isSelf
                                  ? 'opacity-30 cursor-not-allowed text-text-tertiary'
                                  : 'hover:bg-status-critical-soft text-status-critical hover:opacity-80 cursor-pointer'
                              }`}
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </>
                        );
                      })()}
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
              <div className="flex items-center space-x-2.5">
                <img
                  src={telanganaPoliceLogo}
                  alt="Telangana State Police"
                  className="w-5 h-6 object-contain shrink-0"
                />
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
                  <div className="relative">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      value={formData.password}
                      onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                      required={modalMode === 'create'}
                      placeholder={modalMode === 'create' ? 'Enter secure password' : 'Leave blank to keep current'}
                      className="w-full pl-3 pr-10 py-2 bg-elevated-2 border border-border-default rounded-md text-text-primary text-xs focus:outline-none focus:border-accent"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                      title={showPassword ? 'Hide password' : 'Show password'}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-text-tertiary hover:text-text-primary p-1 focus:outline-none cursor-pointer"
                    >
                      {showPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                    </button>
                  </div>
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
                  <label className="block text-text-secondary font-medium mb-1 flex items-center justify-between">
                    <span>Operational Role <span className="text-status-critical">*</span></span>
                    {isEditingSelf && (
                      <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                        [LOCKED]
                      </span>
                    )}
                  </label>
                  <select
                    value={formData.role}
                    onChange={(e) => setFormData({ ...formData, role: e.target.value as UserRole })}
                    disabled={isEditingSelf || (modalMode === 'edit' && selectedUser?.role === 'SUPER_ADMIN' && !isSuperAdmin(currentUser))}
                    className="w-full px-3 py-2 bg-elevated-2 border border-border-default rounded-md text-text-primary text-xs focus:outline-none focus:border-accent cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed"
                  >
                    {isEditingSelf ? (
                      <option value={formData.role}>
                        {formData.role === 'SYS_ADMIN' && (formData.zone || currentUser?.zone)
                          ? 'SYS_ADMIN (Zonal System Admin)'
                          : roleLabel(formData.role, selectedUser || currentUser || undefined)}
                      </option>
                    ) : (
                      <>
                        <option value="CONSTABLE">CONSTABLE (Ground Staff)</option>
                        <option value="SHO">SHO (Station Officer)</option>
                        {currentUser?.role !== 'SYS_ADMIN' && (
                          <>
                            <option value="ACP">ACP (Senior Officer)</option>
                            <option value="SYS_ADMIN">SYS_ADMIN (Zonal System Admin)</option>
                            <option value="MAIN_OFFICER">MAIN_OFFICER (Headquarters Command)</option>
                          </>
                        )}
                        {isSuperAdmin(currentUser) && (
                          <option value="SUPER_ADMIN">SUPER_ADMIN (Super Administrator)</option>
                        )}
                      </>
                    )}
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

              {/* Jurisdiction (Authoritative Cascading: Zone -> Police Station) */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-text-secondary font-medium mb-1">
                    Zone {formData.role === 'CONSTABLE' || formData.role === 'SHO' || formData.role === 'ACP' ? (
                      <span className="text-status-critical">*</span>
                    ) : null}
                  </label>
                  <select
                    value={formData.zone}
                    onChange={(e) => handleZoneChange(e.target.value)}
                    disabled={isEditingSelf || isZonedAdmin}
                    required={formData.role === 'CONSTABLE' || formData.role === 'SHO' || formData.role === 'ACP' || isZonedAdmin}
                    className="w-full px-3 py-2 bg-elevated-2 border border-border-default rounded-md text-text-primary text-xs focus:outline-none focus:border-accent cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed"
                  >
                    {!isZonedAdmin && (
                      <option value="">
                        {formData.role === 'MAIN_OFFICER' ? 'None / City Wide' : 'Select Zone...'}
                      </option>
                    )}
                    {availableZones.map((z) => (
                      <option key={z} value={z}>
                        {z}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-text-secondary font-medium mb-1">
                    Police Station {formData.role === 'CONSTABLE' || formData.role === 'SHO' ? (
                      <span className="text-status-critical">*</span>
                    ) : null}
                  </label>
                  <select
                    value={formData.police_station}
                    onChange={(e) => handleStationChange(e.target.value)}
                    disabled={isEditingSelf || (!formData.zone && formData.role !== 'MAIN_OFFICER')}
                    required={formData.role === 'CONSTABLE' || formData.role === 'SHO'}
                    className="w-full px-3 py-2 bg-elevated-2 border border-border-default rounded-md text-text-primary text-xs focus:outline-none focus:border-accent cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {!formData.zone ? (
                      <option value="">
                        {formData.role === 'MAIN_OFFICER' ? 'None / City Wide' : 'Select Zone First...'}
                      </option>
                    ) : (
                      <>
                        {formData.role !== 'CONSTABLE' && formData.role !== 'SHO' ? (
                          <option value="">None / Zone Wide</option>
                        ) : (
                          <option value="">Select Police Station...</option>
                        )}
                        {filteredStationsForForm.map((s) => {
                          const sName = s.ps_name || s.name || '';
                          const sCode = s.ps_code || s.code || '';
                          return (
                            <option key={s.id} value={sName}>
                              {sName} {sCode ? `(${sCode})` : ''}
                            </option>
                          );
                        })}
                      </>
                    )}
                  </select>
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

                {isEditingSelf && !isSuperAdmin(currentUser) && (
                  <div className="text-[11px] text-amber-400 bg-amber-500/10 border border-amber-500/20 rounded p-2 mb-2">
                    Granular permissions for your own account are locked and can only be modified by a Super Administrator.
                  </div>
                )}

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 bg-base p-3 rounded-md border border-border-subtle max-h-48 overflow-y-auto">
                  {CANONICAL_PERMISSIONS
                    .filter((perm) => {
                      if (isSuperAdmin(currentUser)) return true;
                      const SENSITIVE_PERMISSION_KEYS = ['manage_roles', 'manage_role_templates', 'global_settings', 'manage_geography'];
                      if (SENSITIVE_PERMISSION_KEYS.includes(perm.key)) return false;
                      const callerPerms = currentUser?.effective_permissions || currentUser?.permissions || [];
                      return callerPerms.includes(perm.key);
                    })
                    .map((perm) => {
                    const isChecked = formData.custom_permissions.includes(perm.key);
                    const isPermLocked = isEditingSelf && !isSuperAdmin(currentUser);
                    return (
                      <label
                        key={perm.key}
                        onClick={() => !isPermLocked && togglePermission(perm.key)}
                        className={`flex items-start space-x-2 p-2 rounded transition-colors ${
                          isPermLocked ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer'
                        } ${
                          isChecked ? 'bg-accent/10 border border-accent/25' : 'hover:bg-elevated border border-transparent'
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={isChecked}
                          disabled={isPermLocked}
                          onChange={() => {}}
                          className="mt-0.5 rounded border-border-default bg-elevated-2 text-accent focus:ring-0 shrink-0 disabled:cursor-not-allowed"
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
      {/* Delete Confirmation Modal */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-md bg-elevated border border-status-critical/40 rounded-lg shadow-2xl overflow-hidden">
            <div className="px-5 py-3.5 bg-base border-b border-status-critical/30 flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Trash2 className="w-4 h-4 text-status-critical" />
                <h2 className="text-sm font-semibold text-status-critical uppercase tracking-wider">Permanently Delete Account</h2>
              </div>
              <button
                onClick={closeDeleteModal}
                disabled={deleting}
                className="text-text-tertiary hover:text-text-primary transition-colors cursor-pointer disabled:opacity-50"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-5 space-y-4 text-xs">
              <div className="p-3 bg-status-critical-soft border border-status-critical/25 rounded-md space-y-2">
                <div className="grid grid-cols-2 gap-2 text-[11px]">
                  <div>
                    <span className="text-text-tertiary block text-[10px] uppercase font-medium">Officer Name</span>
                    <span className="font-semibold text-text-primary">
                      {`${deleteTarget.first_name || ''} ${deleteTarget.last_name || ''}`.trim() || deleteTarget.username}
                    </span>
                  </div>
                  <div>
                    <span className="text-text-tertiary block text-[10px] uppercase font-medium">Username</span>
                    <span className="font-semibold text-accent mono">@{deleteTarget.username}</span>
                  </div>
                  <div>
                    <span className="text-text-tertiary block text-[10px] uppercase font-medium">Police ID</span>
                    <span className="mono text-text-secondary">{deleteTarget.police_id || 'N/A'}</span>
                  </div>
                  <div>
                    <span className="text-text-tertiary block text-[10px] uppercase font-medium">Role</span>
                    <span className="font-medium text-text-secondary">{roleLabel(deleteTarget.role)}</span>
                  </div>
                  <div className="col-span-2">
                    <span className="text-text-tertiary block text-[10px] uppercase font-medium">Station / Zone</span>
                    <span className="text-text-secondary">
                      {deleteTarget.police_station || 'All Stations'} / {deleteTarget.zone || 'Hyderabad District'}
                    </span>
                  </div>
                </div>
              </div>

              <p className="text-text-secondary text-[11px] leading-relaxed">
                This permanently deletes the user account. Historical assignments, tracking sessions, reports and audit records are preserved where applicable.
              </p>

              {deleteError && (
                <div className="p-3 bg-status-critical-soft border border-status-critical/30 rounded-md flex items-start space-x-2 text-status-critical">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                  <span>{deleteError}</span>
                </div>
              )}

              <div className="pt-2 border-t border-border-subtle flex items-center justify-end space-x-3">
                <button
                  type="button"
                  onClick={closeDeleteModal}
                  disabled={deleting}
                  className="px-4 py-2 rounded-md border border-border-default text-text-secondary hover:text-text-primary hover:bg-elevated-2 transition-colors cursor-pointer disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleDeleteUser}
                  disabled={deleting}
                  className="px-4 py-2 bg-status-critical hover:opacity-90 disabled:opacity-50 text-white font-semibold rounded-md transition-opacity cursor-pointer flex items-center space-x-1.5"
                >
                  {deleting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  <span>{deleting ? 'Deleting…' : 'Delete Account'}</span>
                </button>
              </div>
            </div>

          </div>
        </div>
      )}
    </div>
  );
};
