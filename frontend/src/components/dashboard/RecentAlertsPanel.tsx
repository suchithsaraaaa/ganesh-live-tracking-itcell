import React, { useMemo } from 'react';
import { AlertTriangle, WifiOff } from 'lucide-react';
import { ActiveMarker } from '../../types';

interface RecentAlertsPanelProps {
  markers: ActiveMarker[];
  onSelectAlert: (marker: ActiveMarker) => void;
}

interface AlertRow {
  marker: ActiveMarker;
  severity: 'critical' | 'warning';
  message: string;
}

export const RecentAlertsPanel: React.FC<RecentAlertsPanelProps> = ({ markers, onSelectAlert }) => {
  const alerts: AlertRow[] = useMemo(() => {
    const rows: AlertRow[] = [];
    markers.forEach((m) => {
      if (m.connection_state === 'OFFLINE') {
        rows.push({ marker: m, severity: 'critical', message: 'GPS signal unavailable' });
      } else if (m.connection_state === 'DEGRADED') {
        rows.push({ marker: m, severity: 'warning', message: 'Degraded telemetry signal' });
      }
    });
    return rows
      .sort((a, b) => new Date(b.marker.last_gps_timestamp).getTime() - new Date(a.marker.last_gps_timestamp).getTime())
      .slice(0, 6);
  }, [markers]);

  return (
    <div className="bg-elevated border border-border-subtle rounded-lg px-4 py-3 flex flex-col flex-1 min-h-0">
      <div className="flex items-center justify-between mb-2.5">
        <h3 className="text-[11px] font-semibold tracking-wider uppercase text-text-primary">
          Recent Alerts
        </h3>
        {alerts.length > 0 && (
          <span className="text-[10px] mono text-text-tertiary">{alerts.length}</span>
        )}
      </div>

      {alerts.length === 0 ? (
        <p className="text-xs text-text-tertiary py-3 text-center">No active alerts</p>
      ) : (
        <div className="flex flex-col overflow-y-auto">
          {alerts.map((a, i) => {
            const Icon = a.severity === 'critical' ? WifiOff : AlertTriangle;
            const color = a.severity === 'critical' ? 'text-status-critical' : 'text-status-warning';
            return (
              <button
                key={a.marker.gpid}
                onClick={() => onSelectAlert(a.marker)}
                className={`flex items-start gap-2.5 py-2 text-left transition-colors hover:bg-elevated-2/60 ${
                  i < alerts.length - 1 ? 'border-b border-border-subtle' : ''
                }`}
              >
                <Icon className={`w-4 h-4 shrink-0 mt-0.5 ${color}`} strokeWidth={1.8} />
                <div className="flex-1 min-w-0">
                  <div className="text-xs text-text-primary truncate">{a.message}</div>
                  <div className="text-[11px] text-text-secondary truncate mono">
                    {a.marker.gpid} &bull; {a.marker.police_station}
                  </div>
                </div>
                <span className="text-[10px] mono text-text-tertiary shrink-0">
                  {new Date(a.marker.last_gps_timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};
