import React, { useMemo } from 'react';
import { ActiveMarker } from '../../types';

interface ZoneStatusPanelProps {
  markers: ActiveMarker[];
  selectedZone: string;
  onSelectZone: (zone: string) => void;
}

interface ZoneRow {
  zone: string;
  total: number;
  active: number;
  holding: number;
  immersed: number;
}

export const ZoneStatusPanel: React.FC<ZoneStatusPanelProps> = ({ markers, selectedZone, onSelectZone }) => {
  const rows: ZoneRow[] = useMemo(() => {
    const byZone = new Map<string, ZoneRow>();
    markers.forEach((m) => {
      const zone = m.zone || 'Unassigned';
      const row = byZone.get(zone) || { zone, total: 0, active: 0, holding: 0, immersed: 0 };
      row.total += 1;
      if (m.procession_state === 'MOVING') row.active += 1;
      if (m.procession_state === 'HOLDING') row.holding += 1;
      if (m.procession_state === 'IMMERSION_COMPLETED') row.immersed += 1;
      byZone.set(zone, row);
    });
    return Array.from(byZone.values()).sort((a, b) => b.total - a.total);
  }, [markers]);

  return (
    <div className="bg-elevated border border-border-subtle rounded-lg px-4 py-3 flex flex-col">
      <div className="flex items-center justify-between mb-2.5">
        <h3 className="text-[11px] font-semibold tracking-wider uppercase text-text-primary">
          Zone Wise Status
        </h3>
        {selectedZone !== 'All Zones' && (
          <button
            onClick={() => onSelectZone('All Zones')}
            className="text-[11px] font-medium text-accent hover:text-accent-hover transition-colors"
          >
            All Zones
          </button>
        )}
      </div>

      {rows.length === 0 ? (
        <p className="text-xs text-text-tertiary py-3 text-center">No active telemetry yet</p>
      ) : (
        <>
          <div className="flex items-center gap-2 text-[10px] font-medium uppercase tracking-wider text-text-tertiary pb-1.5">
            <span className="flex-1">Zone</span>
            <span className="w-10 text-right">Total</span>
            <span className="w-10 text-right">Actv</span>
            <span className="w-10 text-right">Hold</span>
            <span className="w-10 text-right">Imrs</span>
          </div>
          <div className="flex flex-col">
            {rows.map((r, i) => (
              <button
                key={r.zone}
                onClick={() => onSelectZone(selectedZone === r.zone ? 'All Zones' : r.zone)}
                className={`flex items-center gap-2 py-1.5 text-xs text-left transition-colors ${
                  i < rows.length - 1 ? 'border-b border-border-subtle' : ''
                } ${selectedZone === r.zone ? 'text-accent' : 'text-text-secondary hover:text-text-primary'}`}
              >
                <span className={`flex-1 truncate ${selectedZone === r.zone ? 'font-medium' : ''}`}>{r.zone}</span>
                <span className="w-10 text-right mono">{r.total}</span>
                <span className="w-10 text-right mono">{r.active}</span>
                <span className="w-10 text-right mono">{r.holding}</span>
                <span className="w-10 text-right mono">{r.immersed}</span>
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
};
