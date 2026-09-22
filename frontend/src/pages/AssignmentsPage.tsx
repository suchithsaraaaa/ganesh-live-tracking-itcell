import React, { useState } from 'react';
import { Search, UserPlus } from 'lucide-react';
import { useAssignments } from '../hooks/useAssignments';
import { useTracking } from '../context/TrackingContext';
import { fetchIdols } from '../api/client';
import { Idol } from '../types';
import { LoadingState, EmptyState, ErrorState } from '../components/shared/States';

export const AssignmentsPage: React.FC = () => {
  const { assignments, loading, error, reload } = useAssignments();
  const { openAssignment } = useTracking();
  const [onlyActive, setOnlyActive] = useState(true);

  const [gpidSearch, setGpidSearch] = useState('');
  const [searchResults, setSearchResults] = useState<Idol[]>([]);
  const [searching, setSearching] = useState(false);

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

  const visible = onlyActive ? assignments.filter((a) => a.is_active) : assignments;

  return (
    <div className="h-full flex flex-col overflow-hidden animate-fade-in-up">
      <div className="px-6 pt-6 pb-4">
        <h1 className="text-lg font-semibold text-text-primary">Officer Assignment</h1>
        <p className="text-xs text-text-tertiary mt-0.5">
          Assign or hand over ground constables to processions, and review assignment history.
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

      {/* Assignment records */}
      <div className="px-6 flex items-center gap-2 pb-2">
        <h2 className="text-[11px] font-semibold uppercase tracking-wider text-text-primary">Assignment Records</h2>
        <div className="flex items-center gap-1 ml-auto bg-elevated-2 p-1 rounded-md border border-border-default text-[11px]">
          <button
            onClick={() => setOnlyActive(true)}
            className={`px-2.5 py-1 rounded transition-colors ${onlyActive ? 'bg-accent text-base font-medium' : 'text-text-secondary'}`}
          >
            Active
          </button>
          <button
            onClick={() => setOnlyActive(false)}
            className={`px-2.5 py-1 rounded transition-colors ${!onlyActive ? 'bg-accent text-base font-medium' : 'text-text-secondary'}`}
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
              <span className="w-44">GPID</span>
              <span className="w-40">Police Station</span>
              <span className="w-40">Constable</span>
              <span className="w-32">Started</span>
              <span className="w-32">Ended</span>
              <span className="w-20">Status</span>
            </div>
            {visible.map((a, i) => (
              <div
                key={a.id}
                className={`flex items-center gap-2 px-4 py-2.5 text-xs ${i > 0 ? 'border-t border-border-subtle' : ''}`}
              >
                <span className="w-44 mono font-medium text-text-primary truncate">{a.idol_gpid}</span>
                <span className="w-40 text-text-secondary truncate">{a.police_station}</span>
                <span className="w-40 text-text-secondary truncate">{a.constable_name || a.constable_username}</span>
                <span className="w-32 mono text-text-tertiary">{new Date(a.started_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}</span>
                <span className="w-32 mono text-text-tertiary">{a.ended_at ? new Date(a.ended_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' }) : '—'}</span>
                <span className="w-20">
                  <span className={`text-[10px] font-medium uppercase px-1.5 py-0.5 rounded ${a.is_active ? 'bg-status-active-soft text-status-active' : 'bg-status-neutral-soft text-status-neutral'}`}>
                    {a.is_active ? 'Active' : 'Ended'}
                  </span>
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
