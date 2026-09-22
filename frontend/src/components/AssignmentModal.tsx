import React, { useState, useEffect, useMemo } from 'react';
import { X, UserCheck, AlertCircle, ShieldCheck, Search, Loader2, User } from 'lucide-react';
import { assignConstable, handoverAssignment, fetchAssignableOfficers } from '../api/client';
import { AssignableOfficer } from '../types';

interface AssignmentModalProps {
  isOpen: boolean;
  gpid: string;
  currentAssignmentId?: number | null;
  currentConstableName?: string | null;
  onClose: () => void;
  onSuccess: () => void;
}

export const AssignmentModal: React.FC<AssignmentModalProps> = ({
  isOpen,
  gpid,
  currentAssignmentId,
  currentConstableName,
  onClose,
  onSuccess,
}) => {
  const [constableId, setConstableId] = useState<string>('');
  const [reason, setReason] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Officers directory state
  const [officers, setOfficers] = useState<AssignableOfficer[]>([]);
  const [loadingOfficers, setLoadingOfficers] = useState(false);
  const [officersError, setOfficersError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterAvailableOnly, setFilterAvailableOnly] = useState(false);

  const isHandover = Boolean(currentAssignmentId && currentConstableName);

  useEffect(() => {
    if (!isOpen) {
      setConstableId('');
      setReason('');
      setError(null);
      setSuccessMsg(null);
      setSearchQuery('');
      return;
    }

    const loadOfficers = async () => {
      setLoadingOfficers(true);
      setOfficersError(null);
      try {
        const data = await fetchAssignableOfficers();
        setOfficers(data.results || []);
      } catch (err: any) {
        setOfficersError(err.message || 'Failed to load officer directory.');
      } finally {
        setLoadingOfficers(false);
      }
    };

    loadOfficers();
  }, [isOpen]);

  const filteredOfficers = useMemo(() => {
    const q = searchQuery.toLowerCase().trim();
    return officers.filter((officer) => {
      if (filterAvailableOnly && officer.currently_assigned) {
        return false;
      }
      if (!q) return true;
      const matchName = officer.name.toLowerCase().includes(q);
      const matchUsername = officer.username.toLowerCase().includes(q);
      const matchPoliceId = (officer.police_id || '').toLowerCase().includes(q);
      const matchStation = (officer.police_station || '').toLowerCase().includes(q);
      return matchName || matchUsername || matchPoliceId || matchStation;
    });
  }, [officers, searchQuery, filterAvailableOnly]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const parsedId = parseInt(constableId, 10);
    if (isNaN(parsedId)) {
      setError('Please select or specify a valid Constable.');
      return;
    }

    setLoading(true);
    setError(null);
    setSuccessMsg(null);

    try {
      if (isHandover && currentAssignmentId) {
        if (!reason.trim()) {
          setError('Reason is mandatory for duty handover.');
          setLoading(false);
          return;
        }
        await handoverAssignment(currentAssignmentId, parsedId, reason.trim());
        setSuccessMsg(`Duty successfully handed over for GPID ${gpid}.`);
      } else {
        await assignConstable(gpid, parsedId);
        setSuccessMsg(`Constable assigned successfully to GPID ${gpid}.`);
      }
      setTimeout(() => {
        onSuccess();
        onClose();
      }, 1200);
    } catch (err: any) {
      setError(err.message || 'Action failed. Ensure constable is not already assigned to another idol.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg bg-elevated border border-border-default rounded-lg shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-5 py-3.5 bg-base border-b border-border-subtle flex items-center justify-between shrink-0">
          <div className="flex items-center space-x-2">
            <UserCheck className="w-5 h-5 text-status-active" />
            <h2 className="text-sm font-semibold text-text-primary uppercase tracking-wider">
              {isHandover ? 'Handover Constable Duty' : 'Assign Ground Constable'}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="text-text-tertiary hover:text-text-primary transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-5 space-y-4 text-xs overflow-y-auto flex-1">
          <div className="flex items-center justify-between pb-2 border-b border-border-subtle">
            <div>
              <span className="text-text-tertiary text-[11px] block">Target Idol GPID:</span>
              <span className="text-sm font-semibold text-accent mono">{gpid}</span>
            </div>
            {isHandover && (
              <div className="text-right">
                <span className="text-text-tertiary text-[10px] block">Current Officer on Duty:</span>
                <span className="font-medium text-text-primary">{currentConstableName}</span>
              </div>
            )}
          </div>

          {/* Officer Selector */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="block text-text-secondary font-medium">
                {isHandover ? 'Select New Constable' : 'Select Ground Constable'}
              </label>
              <label className="flex items-center space-x-1.5 text-[11px] text-text-tertiary cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={filterAvailableOnly}
                  onChange={(e) => setFilterAvailableOnly(e.target.checked)}
                  className="rounded border-border-default bg-elevated-2 text-status-active focus:ring-0"
                />
                <span>Available only</span>
              </label>
            </div>

            {/* Search filter input */}
            <div className="relative mb-2">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-text-tertiary" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by name, police ID, or police station..."
                className="w-full pl-8 pr-3 py-1.5 bg-elevated-2 border border-border-default rounded-md text-text-primary text-xs focus:outline-none focus:border-status-active"
              />
            </div>

            {/* Officer list box */}
            <div className="border border-border-default rounded-md bg-base max-h-48 overflow-y-auto divide-y divide-border-subtle">
              {loadingOfficers ? (
                <div className="py-6 flex items-center justify-center space-x-2 text-text-tertiary">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Loading officer roster...</span>
                </div>
              ) : officersError ? (
                <div className="p-3 text-status-critical text-[11px] flex items-center space-x-1.5">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{officersError}</span>
                </div>
              ) : filteredOfficers.length === 0 ? (
                <div className="py-6 text-center text-text-tertiary text-[11px]">
                  No matching constables found.
                </div>
              ) : (
                filteredOfficers.map((officer) => {
                  const isSelected = constableId === String(officer.id);
                  return (
                    <div
                      key={officer.id}
                      onClick={() => setConstableId(String(officer.id))}
                      className={`p-2.5 flex items-center justify-between cursor-pointer transition-colors ${
                        isSelected
                          ? 'bg-status-active/15 border-l-2 border-status-active'
                          : 'hover:bg-elevated'
                      }`}
                    >
                      <div className="flex items-center space-x-2.5 min-w-0">
                        <div
                          className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 ${
                            isSelected
                              ? 'bg-status-active text-base font-bold'
                              : 'bg-elevated-2 text-text-secondary'
                          }`}
                        >
                          <User className="w-3.5 h-3.5" />
                        </div>
                        <div className="min-w-0">
                          <div className="flex items-center space-x-2">
                            <span className="font-semibold text-text-primary truncate">
                              {officer.name || officer.username}
                            </span>
                            {officer.police_id && (
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-elevated-2 text-text-secondary mono">
                                ID: {officer.police_id}
                              </span>
                            )}
                          </div>
                          <div className="text-[10px] text-text-tertiary truncate">
                            {officer.police_station || 'Station Unassigned'} &bull; {officer.role}
                          </div>
                        </div>
                      </div>

                      <div className="shrink-0 ml-2 text-right">
                        {officer.currently_assigned ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-status-holding/10 text-status-holding border border-status-holding/20">
                            On Duty ({officer.assigned_gpid || 'GPID'})
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-status-active/10 text-status-active border border-status-active/20">
                            Available
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* Selected confirmation summary */}
            {constableId && (
              <div className="mt-2 p-2 bg-elevated-2 rounded border border-border-default flex items-center justify-between">
                <span className="text-[11px] text-text-secondary">
                  Selected User ID: <span className="mono font-semibold text-text-primary">{constableId}</span>
                </span>
                <button
                  type="button"
                  onClick={() => setConstableId('')}
                  className="text-[11px] text-accent hover:underline cursor-pointer"
                >
                  Clear Selection
                </button>
              </div>
            )}
          </div>

          {isHandover && (
            <div>
              <label className="block text-text-secondary font-medium mb-1">
                Handover Reason / Station Log Notes <span className="text-status-critical">*</span>
              </label>
              <textarea
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                rows={2}
                placeholder="e.g. Shift rotation at Charminar junction"
                required
                className="w-full px-3 py-2 bg-elevated-2 border border-border-default rounded-md text-text-primary text-xs focus:outline-none focus:border-status-active"
              />
            </div>
          )}

          {error && (
            <div className="p-3 bg-status-critical-soft border border-status-critical/30 rounded-md flex items-start space-x-2 text-status-critical text-xs">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {successMsg && (
            <div className="p-3 bg-status-active-soft border border-status-active/30 rounded-md flex items-center space-x-2 text-status-active text-xs">
              <ShieldCheck className="w-4 h-4 shrink-0" />
              <span>{successMsg}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={loading || !constableId}
            className="w-full py-2.5 px-4 bg-status-active hover:opacity-90 disabled:bg-elevated-2 disabled:text-text-tertiary text-base font-medium rounded-md flex items-center justify-center space-x-2 transition-opacity cursor-pointer text-xs disabled:cursor-not-allowed"
          >
            <span>
              {loading
                ? 'Processing Transaction...'
                : isHandover
                ? 'Authorize Duty Handover'
                : 'Confirm Assignment'}
            </span>
          </button>
        </form>
      </div>
    </div>
  );
};
