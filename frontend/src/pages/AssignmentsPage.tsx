import React, { useState } from 'react';
import { Search, UserPlus, UserX, AlertTriangle, AlertCircle, CheckCircle2, X, Loader2 } from 'lucide-react';
import { useAssignments } from '../hooks/useAssignments';
import { useTracking } from '../context/TrackingContext';
import { fetchIdols, endAssignment } from '../api/client';
import { Idol, Assignment } from '../types';
import { LoadingState, EmptyState, ErrorState } from '../components/shared/States';

export const AssignmentsPage: React.FC = () => {
  const { assignments, loading, error, reload } = useAssignments();
  const { openAssignment } = useTracking();
  const [onlyActive, setOnlyActive] = useState(true);

  const [gpidSearch, setGpidSearch] = useState('');
  const [searchResults, setSearchResults] = useState<Idol[]>([]);
  const [searching, setSearching] = useState(false);

  // End assignment modal state
  const [endingAssignment, setEndingAssignment] = useState<Assignment | null>(null);
  const [endReason, setEndReason] = useState('');
  const [endingSubmitting, setEndingSubmitting] = useState(false);
  const [endError, setEndError] = useState<string | null>(null);
  const [successToast, setSuccessToast] = useState<string | null>(null);

  const runSearch = async (value: string) => {
    setGpidSearch(value);
    if (!value.trim()) {
      setSearchResults([]);
      return;
    }
    setSearching(true);
    try {
      const data = await fetchIdols({ search: value.trim() });
      setSearchResults(data.results.slice(0, 8));
    } finally {
      setSearching(false);
    }
  };

  const handleOpenEndModal = (a: Assignment) => {
    setEndingAssignment(a);
    setEndReason('');
    setEndError(null);
  };

  const handleCloseEndModal = () => {
    if (endingSubmitting) return;
    setEndingAssignment(null);
    setEndReason('');
    setEndError(null);
  };

  const handleConfirmEndAssignment = async () => {
    if (!endingAssignment) return;
    setEndingSubmitting(true);
    setEndError(null);
    try {
      await endAssignment(endingAssignment.id, endReason.trim());
      setSuccessToast(`Assignment for ${endingAssignment.idol_gpid} ended successfully.`);
      setTimeout(() => setSuccessToast(null), 4000);
      handleCloseEndModal();
      await reload();
    } catch (err: any) {
      setEndError(err.message || 'Failed to end assignment.');
    } finally {
      setEndingSubmitting(false);
    }
  };

  const visible = onlyActive ? assignments.filter((a) => a.is_active) : assignments;

  return (
    <div className="h-full flex flex-col overflow-hidden animate-fade-in-up relative">
      {/* Toast Notification */}
      {successToast && (
        <div className="fixed top-5 right-6 z-50 flex items-center gap-2 px-4 py-2.5 bg-status-active-soft border border-status-active/40 text-status-active text-xs font-medium rounded-lg shadow-xl animate-fade-in-up">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{successToast}</span>
        </div>
      )}

      <div className="px-6 pt-6 pb-4">
        <h1 className="text-lg font-semibold text-text-primary">Officer Assignment</h1>
        <p className="text-xs text-text-tertiary mt-0.5">
          Assign, hand over, or end ground constable assignments for processions, and review assignment history.
        </p>
      </div>

      {/* Assign by GPID search */}
      <div className="px-6 pb-4">
        <div className="relative max-w-xl">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-text-tertiary" />
          <input
            value={gpidSearch}
            onChange={(e) => runSearch(e.target.value)}
            placeholder="Search GPID or pandal name to assign an officer…"
            className="w-full pl-9 pr-3 py-2.5 bg-elevated-2 border border-border-default rounded-md text-text-primary text-sm mono focus:outline-none focus:border-accent"
          />
        </div>
        {gpidSearch.trim() && (
          <div className="max-w-xl mt-2 bg-elevated border border-border-subtle rounded-md overflow-hidden">
            {searching ? (
              <div className="px-4 py-3 text-xs text-text-tertiary">Searching…</div>
            ) : searchResults.length === 0 ? (
              <div className="px-4 py-3 text-xs text-text-tertiary">No matches</div>
            ) : (
              searchResults.map((idol, i) => (
                <div
                  key={idol.id}
                  className={`flex items-center gap-3 px-4 py-2.5 ${i > 0 ? 'border-t border-border-subtle' : ''}`}
                >
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-medium text-text-primary mono">{idol.gpid}</div>
                    <div className="text-[11px] text-text-secondary truncate">{idol.name} &bull; {idol.police_station}</div>
                  </div>
                  <button
                    onClick={() => openAssignment(idol.gpid)}
                    className="flex items-center gap-1.5 px-2.5 py-1.5 text-[11px] font-medium rounded-md bg-status-active-soft text-status-active hover:opacity-80 transition-opacity shrink-0"
                  >
                    <UserPlus className="w-3.5 h-3.5" />
                    Assign / Handover
                  </button>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {/* Assignment records header & toggle */}
      <div className="px-6 flex items-center gap-2 pb-2">
        <h2 className="text-[11px] font-semibold uppercase tracking-wider text-text-primary">Assignment Records</h2>
        <div className="flex items-center gap-1 ml-auto bg-elevated-2 p-1 rounded-md border border-border-default text-[11px]">
          <button
            onClick={() => setOnlyActive(true)}
            className={`px-2.5 py-1 rounded transition-colors cursor-pointer ${onlyActive ? 'bg-accent text-base font-medium' : 'text-text-secondary hover:text-text-primary'}`}
          >
            Active
          </button>
          <button
            onClick={() => setOnlyActive(false)}
            className={`px-2.5 py-1 rounded transition-colors cursor-pointer ${!onlyActive ? 'bg-accent text-base font-medium' : 'text-text-secondary hover:text-text-primary'}`}
          >
            All History
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-6 pb-6">
        {loading && <LoadingState label="Loading assignment records…" />}
        {!loading && error && <ErrorState message={error} onRetry={reload} />}
        {!loading && !error && visible.length === 0 && (
          <EmptyState title={onlyActive ? 'No active assignments' : 'No assignment history yet'} />
        )}
        {!loading && !error && visible.length > 0 && (
          <div className="bg-elevated border border-border-subtle rounded-lg overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-2 text-[10px] font-medium uppercase tracking-wider text-text-tertiary border-b border-border-subtle">
              <span className="w-40">GPID</span>
              <span className="w-36">Police Station</span>
              <span className="w-36">Constable</span>
              <span className="w-32">Started</span>
              <span className="w-32">Ended</span>
              <span className="w-20">Status</span>
              <span className="flex-1 text-right pr-2">Actions</span>
            </div>
            {visible.map((a, i) => (
              <div
                key={a.id}
                className={`flex items-center gap-2 px-4 py-2.5 text-xs ${i > 0 ? 'border-t border-border-subtle' : ''}`}
              >
                <span className="w-40 mono font-medium text-text-primary truncate">{a.idol_gpid}</span>
                <span className="w-36 text-text-secondary truncate">{a.police_station}</span>
                <span className="w-36 text-text-secondary truncate">{a.constable_name || a.constable_username}</span>
                <span className="w-32 mono text-text-tertiary">{new Date(a.started_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}</span>
                <span className="w-32 mono text-text-tertiary">{a.ended_at ? new Date(a.ended_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' }) : '—'}</span>
                <span className="w-20">
                  <span className={`text-[10px] font-medium uppercase px-1.5 py-0.5 rounded ${a.is_active ? 'bg-status-active-soft text-status-active' : 'bg-status-neutral-soft text-status-neutral'}`}>
                    {a.is_active ? 'Active' : 'Ended'}
                  </span>
                </span>
                <span className="flex-1 flex justify-end pr-2">
                  {a.is_active ? (
                    <button
                      onClick={() => handleOpenEndModal(a)}
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-medium rounded border border-rose-500/30 bg-rose-500/10 text-rose-400 hover:bg-rose-500/20 hover:text-rose-300 transition-colors cursor-pointer"
                      title="End this active assignment"
                    >
                      <UserX className="w-3.5 h-3.5" />
                      <span>End Assignment</span>
                    </button>
                  ) : (
                    <span className="text-[11px] text-text-tertiary italic">Ended</span>
                  )}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* End Assignment Confirmation Modal */}
      {endingAssignment && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-md bg-elevated border border-border-default rounded-lg shadow-2xl overflow-hidden flex flex-col animate-fade-in-up">
            {/* Modal Header */}
            <div className="px-5 py-3.5 bg-base border-b border-border-subtle flex items-center justify-between shrink-0">
              <div className="flex items-center space-x-2">
                <AlertTriangle className="w-4 h-4 text-status-critical" />
                <h2 className="text-sm font-semibold text-text-primary uppercase tracking-wider">
                  End Assignment
                </h2>
              </div>
              <button
                onClick={handleCloseEndModal}
                disabled={endingSubmitting}
                className="text-text-tertiary hover:text-text-primary transition-colors cursor-pointer disabled:opacity-50"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-5 space-y-4 text-xs">
              <div className="p-3.5 bg-elevated-2 border border-border-subtle rounded-md space-y-2">
                <div className="grid grid-cols-2 gap-2 text-[11px]">
                  <div>
                    <span className="text-text-tertiary block text-[10px] uppercase font-medium">GPID</span>
                    <span className="font-semibold text-accent mono">{endingAssignment.idol_gpid}</span>
                  </div>
                  <div>
                    <span className="text-text-tertiary block text-[10px] uppercase font-medium">Police Station</span>
                    <span className="font-medium text-text-primary">{endingAssignment.police_station}</span>
                  </div>
                  <div>
                    <span className="text-text-tertiary block text-[10px] uppercase font-medium">Assigned Officer</span>
                    <span className="font-semibold text-text-primary">
                      {endingAssignment.constable_name || endingAssignment.constable_username}
                    </span>
                  </div>
                  <div>
                    <span className="text-text-tertiary block text-[10px] uppercase font-medium">Started</span>
                    <span className="mono text-text-secondary">
                      {new Date(endingAssignment.started_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}
                    </span>
                  </div>
                  <div className="col-span-2">
                    <span className="text-text-tertiary block text-[10px] uppercase font-medium">Current Status</span>
                    <span className="inline-block mt-0.5 text-[10px] font-semibold uppercase px-2 py-0.5 rounded bg-status-active-soft text-status-active">
                      ACTIVE
                    </span>
                  </div>
                </div>
              </div>

              {/* Warning notice */}
              <div className="p-3 bg-amber-500/10 border border-amber-500/25 rounded-md flex items-start space-x-2 text-amber-300 text-[11px] leading-relaxed">
                <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-amber-400" />
                <span>
                  This will end the officer's active assignment. Historical assignment and tracking records will be preserved.
                </span>
              </div>

              {/* Optional reason */}
              <div>
                <label className="block text-text-secondary font-medium mb-1">
                  Reason for ending (optional)
                </label>
                <input
                  type="text"
                  value={endReason}
                  onChange={(e) => setEndReason(e.target.value)}
                  disabled={endingSubmitting}
                  placeholder="e.g. Shift concluded / Duty rotation / Procession completed"
                  className="w-full px-3 py-2 bg-elevated-2 border border-border-default rounded-md text-text-primary text-xs focus:outline-none focus:border-accent"
                />
              </div>

              {/* Error display if active tracking session blocks ending or other error occurs */}
              {endError && (
                <div className="p-3 bg-status-critical-soft border border-status-critical/30 rounded-md flex items-start space-x-2 text-status-critical text-xs">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                  <span>{endError}</span>
                </div>
              )}

              {/* Modal Actions */}
              <div className="pt-2 border-t border-border-subtle flex items-center justify-end space-x-3">
                <button
                  type="button"
                  onClick={handleCloseEndModal}
                  disabled={endingSubmitting}
                  className="px-4 py-2 rounded-md border border-border-default text-text-secondary hover:text-text-primary hover:bg-elevated-2 transition-colors cursor-pointer disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleConfirmEndAssignment}
                  disabled={endingSubmitting}
                  className="px-4 py-2 bg-rose-600 hover:bg-rose-500 disabled:opacity-50 text-white font-semibold rounded-md transition-colors cursor-pointer flex items-center space-x-1.5 shadow-sm"
                >
                  {endingSubmitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  <span>{endingSubmitting ? 'Ending…' : 'End Assignment'}</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
