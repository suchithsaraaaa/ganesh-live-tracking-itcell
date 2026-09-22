import React, { useEffect, useState } from 'react';
import {
  X,
  MapPin,
  Clock,
  FileText,
  Navigation,
  Shield,
  Layers,
  Phone,
  UserCheck,
  AlertCircle
} from 'lucide-react';
import { ActiveMarker, Idol, ProcessionState } from '../types';
import { fetchIdolDetail, getReportDownloadUrl } from '../api/client';

interface IdolDetailDrawerProps {
  marker: ActiveMarker | null;
  isOpen: boolean;
  onClose: () => void;
  onOpenTimestampLookup: (gpid: string) => void;
  onOpenAssignment: (gpid: string) => void;
  onToggleJourney: (gpid: string) => void;
  isJourneyActive: boolean;
  isLoadingJourney: boolean;
}

const STATE_BADGE_STYLES: Record<ProcessionState, { bg: string; text: string; border: string }> = {
  NOT_STARTED: { bg: 'bg-slate-800', text: 'text-slate-300', border: 'border-slate-700' },
  TRACKING: { bg: 'bg-blue-950', text: 'text-blue-400', border: 'border-blue-800' },
  MOVING: { bg: 'bg-emerald-950', text: 'text-emerald-400', border: 'border-emerald-800' },
  HOLDING: { bg: 'bg-amber-950', text: 'text-amber-400', border: 'border-amber-800' },
  AT_VISARJAN: { bg: 'bg-purple-950', text: 'text-purple-400', border: 'border-purple-800' },
  IMMERSION_COMPLETED: { bg: 'bg-slate-900', text: 'text-slate-400', border: 'border-slate-800' },
};

export const IdolDetailDrawer: React.FC<IdolDetailDrawerProps> = ({
  marker,
  isOpen,
  onClose,
  onOpenTimestampLookup,
  onOpenAssignment,
  onToggleJourney,
  isJourneyActive,
  isLoadingJourney,
}) => {
  const [idolDetail, setIdolDetail] = useState<Idol | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!marker?.gpid) {
      setIdolDetail(null);
      return;
    }

    setLoading(true);
    setError(null);
    fetchIdolDetail(marker.gpid)
      .then((data) => {
        setIdolDetail(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || 'Failed to fetch details');
        setLoading(false);
      });
  }, [marker?.gpid]);

  if (!isOpen || !marker) return null;

  const stateStyle = STATE_BADGE_STYLES[marker.procession_state] || STATE_BADGE_STYLES.NOT_STARTED;

  return (
    <aside className="w-96 bg-slate-950 border-l border-slate-800 flex flex-col h-full z-30 shadow-2xl overflow-hidden shrink-0">
      {/* Header */}
      <div className="p-4 bg-slate-900 border-b border-slate-800 flex items-start justify-between">
        <div>
          <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-0.5">
            Operational Unit
          </div>
          <div className="text-base font-bold text-white mono flex items-center gap-2">
            GPID: <span className="text-blue-400">{marker.gpid}</span>
          </div>
          <div className="text-xs text-slate-300 font-medium truncate max-w-[280px] mt-0.5">
            {marker.idol_name}
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          title="Close details"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Status & Freshness Ribbon */}
      <div className="px-4 py-2 bg-slate-900/60 border-b border-slate-800/80 flex items-center justify-between text-xs">
        <div className={`px-2 py-0.5 rounded border text-[11px] font-semibold ${stateStyle.bg} ${stateStyle.text} ${stateStyle.border}`}>
          {marker.procession_state}
        </div>
        <div className="flex items-center gap-1.5 text-slate-300 text-[11px]">
          <span
            className={`w-2 h-2 rounded-full ${
              marker.connection_state === 'LIVE'
                ? 'bg-emerald-500'
                : marker.connection_state === 'DEGRADED'
                ? 'bg-amber-500'
                : 'bg-rose-500'
            }`}
          />
          <span>Telemetry: <strong className="text-white">{marker.connection_state}</strong></span>
        </div>
      </div>

      {/* Main Scrollable Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
        {/* Quick Operational Actions */}
        <div className="space-y-1.5">
          <div className="text-[10px] font-bold uppercase text-slate-400">Tactical Actions</div>
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => onToggleJourney(marker.gpid)}
              disabled={isLoadingJourney}
              className={`p-2 rounded border text-left flex items-center gap-2 transition-colors ${
                isJourneyActive
                  ? 'bg-blue-600 border-blue-500 text-white'
                  : 'bg-slate-900 border-slate-800 text-slate-300 hover:border-slate-700 hover:bg-slate-850'
              }`}
            >
              <Navigation className="w-4 h-4 shrink-0 text-blue-400" />
              <span className="font-semibold text-[11px]">
                {isLoadingJourney ? 'Loading...' : isJourneyActive ? 'Hide Journey' : 'View Journey'}
              </span>
            </button>

            <button
              onClick={() => onOpenTimestampLookup(marker.gpid)}
              className="p-2 rounded border bg-slate-900 border-slate-800 text-slate-300 hover:border-slate-700 hover:bg-slate-850 text-left flex items-center gap-2 transition-colors"
            >
              <Clock className="w-4 h-4 shrink-0 text-amber-400" />
              <span className="font-semibold text-[11px]">Timestamp Lookup</span>
            </button>
          </div>

          <div className="grid grid-cols-2 gap-2 pt-1">
            <button
              onClick={() => onOpenAssignment(marker.gpid)}
              className="p-2 rounded border bg-slate-900 border-slate-800 text-slate-300 hover:border-slate-700 hover:bg-slate-850 text-left flex items-center gap-2 transition-colors"
            >
              <UserCheck className="w-4 h-4 shrink-0 text-emerald-400" />
              <span className="font-semibold text-[11px]">Assign / Handover</span>
            </button>

            <a
              href={getReportDownloadUrl(marker.gpid)}
              target="_blank"
              rel="noopener noreferrer"
              className="p-2 rounded border bg-slate-900 border-slate-800 text-slate-300 hover:border-slate-700 hover:bg-slate-850 text-left flex items-center gap-2 transition-colors"
            >
              <FileText className="w-4 h-4 shrink-0 text-purple-400" />
              <span className="font-semibold text-[11px]">Official PDF</span>
            </a>
          </div>
        </div>

        {/* Live GPS Telemetry */}
        <div className="p-3 bg-slate-900/80 rounded border border-slate-800 space-y-2">
          <div className="flex items-center justify-between">
            <div className="text-[10px] font-bold uppercase text-slate-400 flex items-center gap-1.5">
              <MapPin className="w-3.5 h-3.5 text-blue-400" /> Current Position
            </div>
            <span className="text-[10px] text-slate-500">
              {new Date(marker.last_gps_timestamp).toLocaleTimeString()}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-[11px]">
            <div>
              <span className="text-slate-500">Latitude:</span>
              <p className="mono font-semibold text-slate-200">{marker.latitude.toFixed(6)}</p>
            </div>
            <div>
              <span className="text-slate-500">Longitude:</span>
              <p className="mono font-semibold text-slate-200">{marker.longitude.toFixed(6)}</p>
            </div>
            <div>
              <span className="text-slate-500">Speed:</span>
              <p className="font-semibold text-slate-200">{marker.speed !== null ? `${marker.speed} km/h` : 'Stationary'}</p>
            </div>
            <div>
              <span className="text-slate-500">GPS Accuracy:</span>
              <p className="font-semibold text-slate-200">{marker.accuracy !== null ? `±${marker.accuracy} m` : 'N/A'}</p>
            </div>
          </div>
        </div>

        {/* Assigned Officer / Constable */}
        <div className="p-3 bg-slate-900/80 rounded border border-slate-800 space-y-2">
          <div className="text-[10px] font-bold uppercase text-slate-400 flex items-center gap-1.5">
            <Shield className="w-3.5 h-3.5 text-emerald-400" /> Assigned Ground Constable
          </div>
          {marker.assigned_constable ? (
            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-white">{marker.assigned_constable.name}</span>
                <span className="mono text-[11px] px-1.5 py-0.5 bg-slate-800 text-slate-300 rounded border border-slate-700">
                  ID: {marker.assigned_constable.police_id}
                </span>
              </div>
              <div className="text-slate-400 text-[11px] flex items-center gap-1">
                <Phone className="w-3 h-3 text-slate-500" />
                <span>{marker.assigned_constable.phone_number || 'Mobile not provided'}</span>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-amber-400 bg-amber-950/30 p-2 rounded border border-amber-900/40">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span className="text-[11px]">No ground constable currently assigned.</span>
            </div>
          )}
        </div>

        {/* Police Station Jurisdiction */}
        <div className="p-3 bg-slate-900/80 rounded border border-slate-800 space-y-2">
          <div className="text-[10px] font-bold uppercase text-slate-400 flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-blue-400" /> Jurisdiction
          </div>
          <div className="grid grid-cols-2 gap-2 text-[11px]">
            <div>
              <span className="text-slate-500">Zone:</span>
              <p className="font-medium text-slate-200">{marker.zone}</p>
            </div>
            <div>
              <span className="text-slate-500">Division:</span>
              <p className="font-medium text-slate-200">{marker.division || 'N/A'}</p>
            </div>
            <div>
              <span className="text-slate-500">Police Station:</span>
              <p className="font-medium text-slate-200">{marker.police_station}</p>
            </div>
            <div>
              <span className="text-slate-500">Station Code:</span>
              <p className="mono font-semibold text-blue-400">{marker.ps_code}</p>
            </div>
          </div>
        </div>

        {/* Physical & Immersion Specs (loaded via API) */}
        {loading && <div className="text-slate-500 text-center py-2">Loading full idol master data...</div>}
        {error && <div className="text-rose-400 text-center py-1">{error}</div>}
        {idolDetail && (
          <div className="p-3 bg-slate-900/80 rounded border border-slate-800 space-y-2">
            <div className="text-[10px] font-bold uppercase text-slate-400">
              Idol & Pandal Specifications
            </div>
            <div className="grid grid-cols-2 gap-2 text-[11px]">
              <div>
                <span className="text-slate-500">Association / Samithi:</span>
                <p className="font-medium text-slate-200 truncate">{idolDetail.association_name || 'Individual'}</p>
              </div>
              <div>
                <span className="text-slate-500">Idol Type:</span>
                <p className="font-medium text-slate-200">{idolDetail.idol_type || 'Standard'}</p>
              </div>
              <div>
                <span className="text-slate-500">Idol Height:</span>
                <p className="font-medium text-slate-200">{idolDetail.idol_height ? `${idolDetail.idol_height} ft` : 'N/A'}</p>
              </div>
              <div>
                <span className="text-slate-500">Pandal Height:</span>
                <p className="font-medium text-slate-200">{idolDetail.pandal_height ? `${idolDetail.pandal_height} ft` : 'N/A'}</p>
              </div>
              <div>
                <span className="text-slate-500">Destination Waterbody:</span>
                <p className="font-medium text-purple-400 truncate">{idolDetail.river_name || 'Hussain Sagar'}</p>
              </div>
              <div>
                <span className="text-slate-500">Immersion Date:</span>
                <p className="font-medium text-slate-200">{idolDetail.immersion_date || 'N/A'}</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
};
