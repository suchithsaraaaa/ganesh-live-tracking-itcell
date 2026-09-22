import React, { useMemo, useState } from 'react';
import { AlertTriangle, WifiOff, Search } from 'lucide-react';
import { useTracking } from '../context/TrackingContext';
import { EmptyState } from '../components/shared/States';

type Severity = 'ALL' | 'critical' | 'warning';

interface AlertRow {
  gpid: string;
  name: string;
  station: string;
  severity: 'critical' | 'warning';
  message: string;
  time: string;
}

export const AlertsPage: React.FC = () => {
  const { activeMarkers, handleSelectMarker } = useTracking();
  const [severity, setSeverity] = useState<Severity>('ALL');
  const [search, setSearch] = useState('');

  const alerts: AlertRow[] = useMemo(() => {
    const rows: AlertRow[] = [];
    activeMarkers.forEach((m) => {
      if (m.connection_state === 'OFFLINE') {
        rows.push({ gpid: m.gpid, name: m.idol_name, station: m.police_station, severity: 'critical', message: 'GPS signal unavailable', time: m.last_gps_timestamp });
      } else if (m.connection_state === 'DEGRADED') {
        rows.push({ gpid: m.gpid, name: m.idol_name, station: m.police_station, severity: 'warning', message: 'Degraded telemetry signal', time: m.last_gps_timestamp });
      }
    });
    return rows
      .filter((a) => severity === 'ALL' || a.severity === severity)
      .filter((a) => !search || a.gpid.toLowerCase().includes(search.toLowerCase()) || a.station.toLowerCase().includes(search.toLowerCase()))
      .sort((a, b) => new Date(b.time).getTime() - new Date(a.time).getTime());
  }, [activeMarkers, severity, search]);

  const critCount = activeMarkers.filter((m) => m.connection_state === 'OFFLINE').length;
  const warnCount = activeMarkers.filter((m) => m.connection_state === 'DEGRADED').length;

  return (
    <div className="h-full flex flex-col overflow-hidden animate-fade-in-up">
      <div className="px-6 pt-6 pb-4">
        <h1 className="text-lg font-semibold text-text-primary">Alerts</h1>
        <p className="text-xs text-text-tertiary mt-0.5">
          Derived from live telemetry freshness — GPIDs with degraded or lost GPS signal.
        </p>
      </div>

      <div className="flex items-center gap-2 px-6 pb-4">
        {(['ALL', 'critical', 'warning'] as Severity[]).map((s) => (
          <button
            key={s}
            onClick={() => setSeverity(s)}
            className={`px-3 py-1.5 rounded-md text-[11px] font-medium uppercase tracking-wide border transition-colors ${
              severity === s
                ? 'bg-elevated-2 border-accent/40 text-text-primary'
                : 'border-border-subtle text-text-tertiary hover:text-text-secondary'
            }`}
          >
            {s === 'ALL' ? `All (${critCount + warnCount})` : s === 'critical' ? `Critical (${critCount})` : `Warning (${warnCount})`}
          </button>
        ))}
        <div className="relative w-56 ml-auto">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-text-tertiary" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search GPID or station…"
            className="w-full pl-8 pr-3 py-1.5 bg-elevated-2 border border-border-default rounded-md text-text-primary text-xs focus:outline-none focus:border-accent"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-6 pb-6">
        {alerts.length === 0 ? (
          <EmptyState title="No active alerts" hint="All tracked GPIDs currently have healthy telemetry." />
        ) : (
          <div className="bg-elevated border border-border-subtle rounded-lg overflow-hidden">
            {alerts.map((a, i) => {
              const Icon = a.severity === 'critical' ? WifiOff : AlertTriangle;
              const color = a.severity === 'critical' ? 'text-status-critical' : 'text-status-warning';
              return (
                <button
                  key={a.gpid}
                  onClick={() => {
                    const marker = activeMarkers.find((m) => m.gpid === a.gpid);
                    if (marker) handleSelectMarker(marker);
                  }}
                  className={`w-full flex items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-elevated-2/60 ${i > 0 ? 'border-t border-border-subtle' : ''}`}
                >
                  <Icon className={`w-4 h-4 shrink-0 ${color}`} strokeWidth={1.8} />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm text-text-primary">{a.message}</div>
                    <div className="text-xs text-text-secondary truncate mono">{a.gpid} &bull; {a.name} &bull; {a.station}</div>
                  </div>
                  <span className="text-[11px] mono text-text-tertiary shrink-0">
                    {new Date(a.time).toLocaleTimeString()}
                  </span>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
