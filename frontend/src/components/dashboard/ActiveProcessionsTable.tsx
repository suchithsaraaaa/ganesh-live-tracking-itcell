import React from 'react';
import { ActiveMarker, ProcessionState } from '../../types';

interface ActiveProcessionsTableProps {
  markers: ActiveMarker[];
  selectedGpid: string | null;
  onSelectMarker: (marker: ActiveMarker) => void;
}

const STATE_LABEL: Record<ProcessionState, string> = {
  NOT_STARTED: 'Not Started',
  TRACKING: 'Tracking',
  MOVING: 'Moving',
  HOLDING: 'Holding',
  AT_VISARJAN: 'At Visarjan',
  IMMERSION_COMPLETED: 'Immersed',
};

const STATE_COLOR: Record<ProcessionState, string> = {
  NOT_STARTED: 'var(--color-status-neutral)',
  TRACKING: 'var(--color-status-tracking)',
  MOVING: 'var(--color-status-active)',
  HOLDING: 'var(--color-status-warning)',
  AT_VISARJAN: 'var(--color-status-visarjan)',
  IMMERSION_COMPLETED: 'var(--color-status-neutral)',
};

const COLS = [
  { key: 'gpid', label: 'GPID', width: 'w-44' },
  { key: 'zone', label: 'Zone', width: 'w-24' },
  { key: 'ps', label: 'Police Station', width: 'w-40' },
  { key: 'status', label: 'Status', width: 'w-28' },
  { key: 'assignment', label: 'Assignment', width: 'w-40' },
  { key: 'location', label: 'Last Location', width: 'flex-1' },
  { key: 'update', label: 'Last Update', width: 'w-24' },
];

export const ActiveProcessionsTable: React.FC<ActiveProcessionsTableProps> = ({
  markers,
  selectedGpid,
  onSelectMarker,
}) => {
  return (
    <div className="flex flex-col min-h-0 overflow-x-auto">
      <div className="flex items-center gap-2 px-1 pb-2 min-w-[880px] text-[10px] font-medium uppercase tracking-wider text-text-tertiary">
        {COLS.map((c) => (
          <span key={c.key} className={c.width}>{c.label}</span>
        ))}
      </div>

      {markers.length === 0 ? (
        <div className="py-10 text-center text-xs text-text-tertiary bg-elevated border border-border-subtle rounded-lg min-w-[880px]">
          No active processions
        </div>
      ) : (
        <div className="bg-elevated border border-border-subtle rounded-lg overflow-hidden min-w-[880px]">
          {markers.map((m, i) => {
            const isSelected = selectedGpid === m.gpid;
            return (
              <button
                key={m.gpid}
                onClick={() => onSelectMarker(m)}
                className={`w-full flex items-center gap-2 px-3 py-2.5 text-left text-xs transition-colors ${
                  i > 0 ? 'border-t border-border-subtle' : ''
                } ${isSelected ? 'bg-elevated-2' : 'hover:bg-elevated-2/60'}`}
              >
                <span className="w-44 mono font-medium text-text-primary truncate">{m.gpid}</span>
                <span className="w-24 text-text-secondary truncate">{m.zone}</span>
                <span className="w-40 text-text-secondary truncate">{m.police_station}</span>
                <span className="w-28 flex items-center gap-1.5">
                  <span
                    className="w-1.5 h-1.5 rounded-full shrink-0"
                    style={{ backgroundColor: STATE_COLOR[m.procession_state] }}
                  />
                  <span
                    className="text-[11px] font-medium uppercase tracking-wide"
                    style={{ color: STATE_COLOR[m.procession_state] }}
                  >
                    {STATE_LABEL[m.procession_state]}
                  </span>
                </span>
                <span className="w-40 text-text-secondary truncate">
                  {m.assigned_constable?.name || 'Unassigned'}
                </span>
                <span className="flex-1 mono text-text-secondary truncate">
                  {m.latitude.toFixed(4)}, {m.longitude.toFixed(4)}
                </span>
                <span className="w-24 mono text-text-tertiary">
                  {new Date(m.last_gps_timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};
