import React, { useState, useEffect, useMemo } from 'react';
import {
  ShieldCheck,
  Shield,
  KeyRound,
  Users,
  CheckCircle2,
  AlertTriangle,
  Info,
  Edit2,
  Check,
  X,
  Loader2,
  ArrowRight,
  Lock,
} from 'lucide-react';
import { fetchRoleTemplates, updateRoleTemplate } from '../api/client';
import { RolePermissionTemplate, UserRole } from '../types';
import { useAuth, isSuperAdmin, roleLabel } from '../context/AuthContext';
import { LoadingState, ErrorState } from '../components/shared/States';

interface CapabilityMeta {
  key: string;
  label: string;
  desc: string;
  category: string;
}

const ALL_CAPABILITIES: CapabilityMeta[] = [
  // Dashboard
  { key: 'view_dashboard', label: 'View Dashboard', desc: 'Access command overview, counts, and live procession status', category: 'Dashboard' },

  // Idols
  { key: 'view_idols', label: 'View Idols', desc: 'Browse and search registered Ganesh idols', category: 'Idols' },
  { key: 'view_gpids', label: 'View GPIDs', desc: 'Authoritative idol identifiers and references', category: 'Idols' },
  { key: 'view_police_stations', label: 'View Police Stations', desc: 'View authoritative station listings and boundaries', category: 'Idols' },
  { key: 'view_holding_points', label: 'View Holding Points', desc: 'Inspect congestion and buffer holding points', category: 'Idols' },
  { key: 'view_visarjan_points', label: 'View Visarjan Points', desc: 'Inspect water body immersion points and tanks', category: 'Idols' },

  // Live Operations
  { key: 'view_live_map', label: 'View Live Map', desc: 'Real-time GPS tracking map with markers and status', category: 'Live Operations' },
  { key: 'view_processions', label: 'View Processions', desc: 'Monitor active procession movements and transit states', category: 'Live Operations' },
  { key: 'view_journey', label: 'View Journey & Breadcrumbs', desc: 'Historical GPS routes and breadcrumb trails', category: 'Live Operations' },
  { key: 'view_tracking_history', label: 'View Tracking History', desc: 'Detailed GPS session logs and point records', category: 'Live Operations' },
  { key: 'ingest_telemetry', label: 'Ingest Telemetry', desc: 'Receive and transmit live GPS location points', category: 'Live Operations' },
  { key: 'view_officer_locations', label: 'View Officer Locations', desc: 'View constable live coordinates and device state', category: 'Live Operations' },

  // Assignments
  { key: 'view_assignments', label: 'View Assignments', desc: 'Oversight of officer duties and idol pairings', category: 'Assignments' },
  { key: 'assign_field_officers', label: 'Assign Field Officers', desc: 'Pair constables with operational idols', category: 'Assignments' },
  { key: 'create_assignments', label: 'Create Assignments', desc: 'Initiate new duty assignments', category: 'Assignments' },
  { key: 'reassign_assignments', label: 'Reassign Officers', desc: 'Transfer idol duties to alternative officers', category: 'Assignments' },
  { key: 'manage_assignments', label: 'Manage Assignments', desc: 'Complete assignment lifecycle management and termination', category: 'Assignments' },
  { key: 'handover_duty', label: 'Handover Duty', desc: 'Execute on-ground duty handovers between officers', category: 'Assignments' },

  // Reports
  { key: 'view_reports', label: 'View Reports', desc: 'Browse generated operational PDF reports', category: 'Reports' },
  { key: 'generate_reports', label: 'Generate Reports', desc: 'Create authoritative PDF immersion reports', category: 'Reports' },
  { key: 'export_reports', label: 'Export Reports', desc: 'Download CSV and PDF data exports', category: 'Reports' },

  // System & Audits
  { key: 'view_audit_logs', label: 'View Audit Logs', desc: 'Review administrative and operational audit trail', category: 'System & Audits' },
  { key: 'view_alerts', label: 'View Alerts', desc: 'Receive geofence violation and stoppage alerts', category: 'System & Audits' },
  { key: 'manage_geography', label: 'Manage Geography', desc: 'Manage station boundaries and geofencing polygons', category: 'System & Audits' },

  // User & Role Management
  { key: 'manage_users', label: 'Manage Users', desc: 'Create, update, and manage officer accounts', category: 'User Management' },
  { key: 'manage_permissions', label: 'Manage Permissions', desc: 'Assign granular user capability overrides', category: 'User Management' },
  { key: 'manage_roles', label: 'Manage Roles', desc: 'Assign and upgrade user operational roles', category: 'Role Management' },
  { key: 'manage_role_templates', label: 'Manage Role Templates', desc: 'Global role default capabilities configuration', category: 'Role Management' },
];

const CATEGORIES = [
  'Dashboard',
  'Idols',
  'Live Operations',
  'Assignments',
  'Reports',
  'System & Audits',
  'User Management',
  'Role Management',
];

export const RolesPage: React.FC = () => {
  const { user: currentUser } = useAuth();
  const [templates, setTemplates] = useState<RolePermissionTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Edit Modal State
  const [editingTemplate, setEditingTemplate] = useState<RolePermissionTemplate | null>(null);
  const [selectedPermissions, setSelectedPermissions] = useState<string[]>([]);
  const [descriptionInput, setDescriptionInput] = useState<string>('');
  const [isConfirmingDiff, setIsConfirmingDiff] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveSuccessMessage, setSaveSuccessMessage] = useState<string | null>(null);

  const canEdit = isSuperAdmin(currentUser);

  const loadTemplates = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchRoleTemplates();
      setTemplates(data.results || []);
    } catch (err: any) {
      setError(err?.message || 'Failed to load role templates');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTemplates();
  }, []);

  const handleOpenEdit = (template: RolePermissionTemplate) => {
    setEditingTemplate(template);
    setSelectedPermissions([...(template.permissions || [])]);
    setDescriptionInput(template.description || '');
    setIsConfirmingDiff(false);
  };

  const handleCloseEdit = () => {
    setEditingTemplate(null);
    setSelectedPermissions([]);
    setDescriptionInput('');
    setIsConfirmingDiff(false);
  };

  const togglePermission = (key: string) => {
    setSelectedPermissions((prev) =>
      prev.includes(key) ? prev.filter((p) => p !== key) : [...prev, key]
    );
  };

  const handleToggleCategory = (cat: string) => {
    const catKeys = ALL_CAPABILITIES.filter((c) => c.category === cat).map((c) => c.key);
    const allSelected = catKeys.every((k) => selectedPermissions.includes(k));
    if (allSelected) {
      setSelectedPermissions((prev) => prev.filter((k) => !catKeys.includes(k)));
    } else {
      setSelectedPermissions((prev) => Array.from(new Set([...prev, ...catKeys])));
    }
  };

  // Diff computation for confirmation modal
  const diffSummary = useMemo(() => {
    if (!editingTemplate) return { added: [], removed: [], unchanged: [] };
    const original = new Set(editingTemplate.permissions || []);
    const current = new Set(selectedPermissions);

    const added = selectedPermissions.filter((p) => !original.has(p));
    const removed = (editingTemplate.permissions || []).filter((p) => !current.has(p));
    const unchanged = selectedPermissions.filter((p) => original.has(p));

    return { added, removed, unchanged };
  }, [editingTemplate, selectedPermissions]);

  const handleConfirmSave = async () => {
    if (!editingTemplate) return;
    try {
      setSaving(true);
      const res = await updateRoleTemplate(editingTemplate.role, {
        permissions: selectedPermissions,
        description: descriptionInput.trim(),
      });
      setSaveSuccessMessage(
        `Default permissions for ${roleLabel(editingTemplate.role)} updated successfully (+${res.added?.length || 0} added, -${res.removed?.length || 0} removed).`
      );
      setTimeout(() => setSaveSuccessMessage(null), 6000);
      handleCloseEdit();
      await loadTemplates();
    } catch (err: any) {
      alert(err?.message || 'Failed to update role template');
    } finally {
      setSaving(false);
    }
  };

  const getRoleBadgeStyle = (role: UserRole) => {
    switch (role) {
      case 'SUPER_ADMIN':
        return 'bg-amber-500/20 text-amber-300 border-amber-500/40 font-bold';
      case 'MAIN_OFFICER':
        return 'bg-blue-500/20 text-blue-300 border-blue-500/40';
      case 'SYS_ADMIN':
        return 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40';
      case 'ACP':
        return 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40';
      case 'SHO':
        return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40';
      case 'CONSTABLE':
        return 'bg-slate-500/20 text-slate-300 border-slate-500/40';
      default:
        return 'bg-elevated-2 text-text-secondary border-border-default';
    }
  };

  const getRoleScope = (role: UserRole) => {
    switch (role) {
      case 'SUPER_ADMIN':
        return 'Global Unrestricted (City-Wide)';
      case 'MAIN_OFFICER':
        return 'Headquarters Command (City-Wide / Assigned Zone)';
      case 'SYS_ADMIN':
        return 'Zone-Scoped Administrative Jurisdiction';
      case 'ACP':
        return 'Division / Zone Supervisory Jurisdiction';
      case 'SHO':
        return 'Police Station Operational Jurisdiction';
      case 'CONSTABLE':
        return 'Assigned GPID Only (Field Duty)';
      default:
        return 'Standard Operational Scope';
    }
  };

  return (
    <div className="h-full flex flex-col overflow-hidden bg-background">
      {/* Header */}
      <div className="px-6 py-5 border-b border-border-subtle bg-elevated/40">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <KeyRound className="w-5 h-5 text-accent" />
              <h1 className="text-xl font-bold tracking-tight text-text-primary">ROLES & PERMISSIONS</h1>
              <span className="px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider bg-accent/15 text-accent border border-accent/30">
                Operational RBAC
              </span>
            </div>
            <p className="text-xs text-text-secondary mt-0.5">
              Manage default capabilities assigned to each operational role across the Hyderabad Police tracking platform.
            </p>
          </div>

          <div className="flex items-center gap-2">
            {canEdit ? (
              <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs font-medium">
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>Super Administrator Authorized</span>
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-elevated border border-border-default text-text-tertiary text-xs">
                <Lock className="w-3.5 h-3.5" />
                <span>Read-Only View (Super Admin Required to Edit)</span>
              </span>
            )}
          </div>
        </div>

        {/* Informational Architecture Banner */}
        <div className="mt-3 p-3 rounded-md bg-elevated-2/70 border border-border-subtle text-xs text-text-secondary flex items-start gap-2.5">
          <Info className="w-4 h-4 text-accent shrink-0 mt-0.5" />
          <div className="leading-relaxed">
            <span className="font-semibold text-text-primary">Two-Tier RBAC Architecture:</span> Roles define the default capabilities that accounts automatically inherit. In <span className="text-text-primary font-medium">Administration → Users</span>, administrators can selectively grant per-officer <span className="italic">Granular Capabilities & Permissions</span> overrides without altering these role-wide templates.
          </div>
        </div>

        {saveSuccessMessage && (
          <div className="mt-3 p-3 rounded-md bg-status-success/15 border border-status-success/30 text-status-success text-xs flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{saveSuccessMessage}</span>
          </div>
        )}
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {loading && <LoadingState label="Loading role templates…" />}
        {!loading && error && <ErrorState message={error} onRetry={loadTemplates} />}

        {!loading && !error && (
          <div className="grid grid-cols-1 gap-4">
            {templates.map((tpl) => {
              const role = tpl.role;
              const isSuper = role === 'SUPER_ADMIN';
              const perms = tpl.permissions || [];

              return (
                <div
                  key={role}
                  className={`bg-elevated border rounded-lg p-5 transition-all ${
                    isSuper
                      ? 'border-amber-500/40 bg-gradient-to-r from-amber-500/5 via-elevated to-elevated'
                      : 'border-border-subtle hover:border-border-default'
                  }`}
                >
                  <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-border-subtle/60">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2.5">
                        <span className={`px-2.5 py-1 rounded text-xs border mono ${getRoleBadgeStyle(role)}`}>
                          {role}
                        </span>
                        <h2 className="text-base font-semibold text-text-primary">
                          {tpl.role_display || roleLabel(role)}
                        </h2>
                        {isSuper && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-amber-500/20 text-amber-300 border border-amber-500/40 flex items-center gap-1">
                            <ShieldCheck className="w-3 h-3" />
                            Highest Authority
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-text-secondary leading-normal">
                        {tpl.description || getRoleScope(role)}
                      </p>
                    </div>

                    <div className="flex items-center gap-4 shrink-0">
                      <div className="text-right">
                        <div className="text-xs font-semibold text-text-primary flex items-center gap-1.5 justify-end">
                          <Users className="w-3.5 h-3.5 text-text-tertiary" />
                          <span>{tpl.user_count} {tpl.user_count === 1 ? 'account' : 'accounts'}</span>
                        </div>
                        <div className="text-[11px] text-text-tertiary">
                          Scope: {getRoleScope(role).split('(')[0].trim()}
                        </div>
                      </div>

                      <button
                        onClick={() => handleOpenEdit(tpl)}
                        disabled={!canEdit}
                        className={`px-3 py-1.5 rounded text-xs font-medium border flex items-center gap-1.5 transition-colors cursor-pointer ${
                          canEdit
                            ? 'bg-accent/15 border-accent/40 text-accent hover:bg-accent/25'
                            : 'bg-elevated border-border-subtle text-text-tertiary cursor-not-allowed opacity-50'
                        }`}
                        title={canEdit ? 'Edit default permissions' : 'Super Administrator required to modify templates'}
                      >
                        <Edit2 className="w-3 h-3" />
                        <span>Edit Defaults</span>
                      </button>
                    </div>
                  </div>

                  {/* Capabilities tags */}
                  <div className="pt-3">
                    <div className="flex items-center justify-between text-[11px] text-text-tertiary mb-2">
                      <span className="font-semibold uppercase tracking-wider">
                        Default Capabilities ({perms.length} assigned)
                      </span>
                      {tpl.updated_at && (
                        <span>
                          Last updated: {new Date(tpl.updated_at).toLocaleDateString()} {tpl.updated_by_name ? `by ${tpl.updated_by_name}` : ''}
                        </span>
                      )}
                    </div>

                    <div className="flex flex-wrap gap-1.5">
                      {perms.map((p) => {
                        const meta = ALL_CAPABILITIES.find((c) => c.key === p);
                        return (
                          <span
                            key={p}
                            title={meta?.desc || p}
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] bg-elevated-2 border border-border-subtle text-text-secondary hover:text-text-primary hover:border-border-default transition-colors"
                          >
                            <Check className="w-2.5 h-2.5 text-status-success shrink-0" />
                            <span>{meta?.label || p}</span>
                          </span>
                        );
                      })}
                      {perms.length === 0 && (
                        <span className="text-xs text-text-tertiary italic">No default permissions assigned.</span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Edit Role Template Modal */}
      {editingTemplate && !isConfirmingDiff && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-xs">
          <div className="bg-elevated border border-border-default rounded-xl w-full max-w-3xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-border-subtle flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <Shield className="w-5 h-5 text-accent" />
                <div>
                  <h3 className="text-base font-bold text-text-primary">
                    Edit Default Permissions — {editingTemplate.role_display || roleLabel(editingTemplate.role)}
                  </h3>
                  <p className="text-[11px] text-text-tertiary">
                    Configure baseline capabilities inherited by all {editingTemplate.user_count} accounts with role {editingTemplate.role}.
                  </p>
                </div>
              </div>
              <button
                onClick={handleCloseEdit}
                className="p-1 text-text-tertiary hover:text-text-primary rounded hover:bg-elevated-2"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto p-6 space-y-5 text-xs">
              {/* Description Edit */}
              <div>
                <label className="block text-text-secondary font-medium mb-1">Role Description / Operational Scope</label>
                <input
                  type="text"
                  value={descriptionInput}
                  onChange={(e) => setDescriptionInput(e.target.value)}
                  placeholder="e.g. Headquarters command and oversight across all city zones..."
                  className="w-full px-3 py-2 bg-elevated-2 border border-border-default rounded-md text-text-primary focus:outline-none focus:border-accent text-xs"
                />
              </div>

              {/* Capabilities checklist grouped by category */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-text-primary uppercase tracking-wider text-[11px]">
                    Available Capabilities ({selectedPermissions.length} / {ALL_CAPABILITIES.length} selected)
                  </span>
                  <div className="flex gap-2 text-[11px]">
                    <button
                      type="button"
                      onClick={() => setSelectedPermissions(ALL_CAPABILITIES.map((c) => c.key))}
                      className="text-accent hover:underline cursor-pointer"
                    >
                      Select All
                    </button>
                    <span className="text-border-default">|</span>
                    <button
                      type="button"
                      onClick={() => setSelectedPermissions([])}
                      className="text-text-tertiary hover:text-text-primary cursor-pointer"
                    >
                      Clear All
                    </button>
                  </div>
                </div>

                {CATEGORIES.map((cat) => {
                  const catCapabilities = ALL_CAPABILITIES.filter((c) => c.category === cat);
                  const selectedCount = catCapabilities.filter((c) => selectedPermissions.includes(c.key)).length;
                  const allSelected = selectedCount === catCapabilities.length;

                  return (
                    <div key={cat} className="border border-border-subtle rounded-md bg-elevated-2/40 overflow-hidden">
                      <div className="px-3 py-2 bg-elevated-2 border-b border-border-subtle flex items-center justify-between">
                        <span className="font-semibold text-text-primary text-xs">{cat}</span>
                        <button
                          type="button"
                          onClick={() => handleToggleCategory(cat)}
                          className="text-[11px] text-accent hover:underline cursor-pointer"
                        >
                          {allSelected ? 'Deselect Category' : 'Select Category'}
                        </button>
                      </div>

                      <div className="p-3 grid grid-cols-1 md:grid-cols-2 gap-2">
                        {catCapabilities.map((cap) => {
                          const checked = selectedPermissions.includes(cap.key);
                          return (
                            <label
                              key={cap.key}
                              className={`flex items-start gap-2.5 p-2 rounded border cursor-pointer transition-colors ${
                                checked
                                  ? 'bg-accent/10 border-accent/30 text-text-primary'
                                  : 'bg-elevated/50 border-transparent hover:border-border-subtle text-text-secondary'
                              }`}
                            >
                              <input
                                type="checkbox"
                                checked={checked}
                                onChange={() => togglePermission(cap.key)}
                                className="mt-0.5 rounded border-border-default text-accent focus:ring-accent"
                              />
                              <div className="leading-tight">
                                <div className="font-medium text-text-primary text-xs">{cap.label}</div>
                                <div className="text-[10px] text-text-tertiary mt-0.5">{cap.desc}</div>
                              </div>
                            </label>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-3.5 border-t border-border-subtle bg-elevated-2 flex items-center justify-between">
              <button
                type="button"
                onClick={handleCloseEdit}
                className="px-4 py-2 rounded text-xs text-text-secondary hover:text-text-primary border border-border-default cursor-pointer"
              >
                Cancel
              </button>

              <button
                type="button"
                onClick={() => setIsConfirmingDiff(true)}
                className="px-4 py-2 rounded text-xs font-semibold bg-accent text-background hover:bg-accent-hover flex items-center gap-1.5 cursor-pointer shadow-sm"
              >
                <span>Review Changes & Confirm</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Safety Confirmation / Diff Modal (Phase 11 Requirement) */}
      {editingTemplate && isConfirmingDiff && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-xs">
          <div className="bg-elevated border border-amber-500/40 rounded-xl w-full max-w-xl shadow-2xl overflow-hidden flex flex-col">
            <div className="px-6 py-4 border-b border-border-subtle bg-amber-500/10 flex items-center gap-2.5">
              <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0" />
              <div>
                <h3 className="text-base font-bold text-text-primary">
                  Confirm Role Template Update: {editingTemplate.role_display || roleLabel(editingTemplate.role)}
                </h3>
                <p className="text-[11px] text-amber-300">
                  Please review the exact changes being applied across all accounts under this role.
                </p>
              </div>
            </div>

            <div className="p-6 space-y-4 text-xs">
              <div className="p-3 rounded bg-elevated-2 border border-border-subtle text-text-secondary">
                <span className="font-semibold text-text-primary">Scope of Impact:</span> This action updates the authoritative baseline defaults for{' '}
                <span className="font-bold text-accent">{editingTemplate.user_count} existing {editingTemplate.role} accounts</span> as well as all future accounts created with this role. Officers with explicit granular overrides retain their custom overrides.
              </div>

              {/* Added Capabilities */}
              <div>
                <span className="font-semibold text-status-success flex items-center gap-1 mb-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Capabilities Being Added ({diffSummary.added.length})
                </span>
                {diffSummary.added.length > 0 ? (
                  <div className="flex flex-wrap gap-1 p-2 rounded bg-status-success/10 border border-status-success/20">
                    {diffSummary.added.map((p) => (
                      <span key={p} className="px-2 py-0.5 rounded text-[11px] bg-status-success/20 text-status-success font-medium">
                        + {ALL_CAPABILITIES.find((c) => c.key === p)?.label || p}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-[11px] text-text-tertiary italic pl-1">None</p>
                )}
              </div>

              {/* Removed Capabilities */}
              <div>
                <span className="font-semibold text-status-critical flex items-center gap-1 mb-1.5">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  Capabilities Being Removed ({diffSummary.removed.length})
                </span>
                {diffSummary.removed.length > 0 ? (
                  <div className="flex flex-wrap gap-1 p-2 rounded bg-status-critical/10 border border-status-critical/20">
                    {diffSummary.removed.map((p) => (
                      <span key={p} className="px-2 py-0.5 rounded text-[11px] bg-status-critical/20 text-status-critical font-medium">
                        - {ALL_CAPABILITIES.find((c) => c.key === p)?.label || p}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-[11px] text-text-tertiary italic pl-1">None</p>
                )}
              </div>

              <div className="text-[11px] text-text-tertiary pt-2 border-t border-border-subtle">
                A security audit record (<code className="mono text-accent">ROLE_TEMPLATE_UPDATED</code>) will be recorded permanently with your officer credentials and IP address.
              </div>
            </div>

            <div className="px-6 py-3.5 border-t border-border-subtle bg-elevated-2 flex items-center justify-between">
              <button
                type="button"
                onClick={() => setIsConfirmingDiff(false)}
                disabled={saving}
                className="px-4 py-2 rounded text-xs text-text-secondary hover:text-text-primary border border-border-default cursor-pointer"
              >
                Back to Edit
              </button>

              <button
                type="button"
                onClick={handleConfirmSave}
                disabled={saving}
                className="px-4 py-2 rounded text-xs font-semibold bg-accent text-background hover:bg-accent-hover flex items-center gap-1.5 cursor-pointer shadow-sm"
              >
                {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                <span>{saving ? 'Updating Template…' : 'Confirm & Apply Updates'}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
