import React, { useMemo } from 'react';
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
  { key: 'gpid', label: 'GPID', width: 'w-40' },
  { key: 'height', label: 'Height', width: 'w-24' },
  { key: 'zone', label: 'Zone', width: 'w-24' },
  { key: 'ps', label: 'Police Station', width: 'w-36' },
  { key: 'status', label: 'Status', width: 'w-28' },
  { key: 'assignment', label: 'Assignment', width: 'w-36' },
  { key: 'location', label: 'Last Location', width: 'flex-1' },
  { key: 'update', label: 'Last Update', width: 'w-24' },
];

export const ActiveProcessionsTable: React.FC<ActiveProcessionsTableProps> = ({
  markers,
  selectedGpid,
  onSelectMarker,
}) => {
  // Guarantee ONE GPID = ONE ROW and ONLY actual active processions (Rule 9 & 10)
  const uniqueRows = useMemo(() => {
    const seen = new Set<string>();
    const list: ActiveMarker[] = [];
    for (const m of markers) {
      // Must be an active tracking session or active procession state (not un-started origin marker)
      const isActualActive = !m.is_origin_marker || (m.procession_state && m.procession_state !== 'NOT_STARTED');
      if (!isActualActive) continue;
      if (!seen.has(m.gpid)) {
        seen.add(m.gpid);
        list.push(m);
      }
    }
    return list;
  }, [markers]);

  return (
    <div className="flex flex-col min-h-0 overflow-x-auto">
      <div className="flex items-center gap-2 px-1 pb-2 min-w-[920px] text-[10px] font-medium uppercase tracking-wider text-text-tertiary">
        {COLS.map((c) => (
          <span key={c.key} className={c.width}>{c.label}</span>
        ))}
      </div>

      {uniqueRows.length === 0 ? (
        <div className="py-10 text-center text-xs text-text-tertiary bg-elevated border border-border-subtle rounded-lg min-w-[920px]">
          No active processions
        </div>
      ) : (
        <div className="bg-elevated border border-border-subtle rounded-lg overflow-hidden min-w-[920px]">
          {uniqueRows.map((m, i) => {
            const isSelected = selectedGpid === m.gpid;
            const isSubthreshold = m.height_classification === 'SUBTHRESHOLD' || (m.idol_height && m.idol_height < 15);
            const heightBadgeColor =
              m.height_classification === 'RED' || (m.idol_height && m.idol_height >= 26)
                ? '#EF4444'
                : m.height_classification === 'YELLOW' || (m.idol_height && m.idol_height >= 21)
                ? '#F59E0B'
                : isSubthreshold
                ? '#06B6D4'
                : '#10B981';

            return (
              <button
                key={m.gpid}
                onClick={() => onSelectMarker(m)}
                className={`w-full flex items-center gap-2 px-3 py-2.5 text-left text-xs transition-colors ${
                  i > 0 ? 'border-t border-border-subtle' : ''
                } ${isSelected ? 'bg-elevated-2' : 'hover:bg-elevated-2/60'}`}
              >
                <span className="w-40 mono font-medium text-text-primary truncate">{m.gpid}</span>
                <span className="w-24">
                  <span
                    className="text-[10px] font-bold px-1.5 py-0.5 rounded border"
                    style={{
                      color: heightBadgeColor,
                      borderColor: `${heightBadgeColor}50`,
                      backgroundColor: `${heightBadgeColor}15`,
                    }}
                  >
                    {m.idol_height ? `${m.idol_height} ft` : '<15 ft'}
                  </span>
                </span>
                <span className="w-24 text-text-secondary truncate">{m.zone}</span>
                <span className="w-36 text-text-secondary truncate">{m.police_station}</span>
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
                <span className="w-36 text-text-secondary truncate">
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
