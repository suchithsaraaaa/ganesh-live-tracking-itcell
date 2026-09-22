import React, { useEffect, useMemo, useState } from 'react';
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
  AlertCircle,
  Route as RouteIcon,
  LucideIcon,
} from 'lucide-react';
import { ActiveMarker, Idol, JourneyBreadcrumb, ProcessionState } from '../types';
import { fetchIdolDetail, fetchJourney, getReportDownloadUrl } from '../api/client';

interface IdolDetailDrawerProps {
  marker: ActiveMarker | null;
  isOpen: boolean;
  onClose: () => void;
  onOpenTimestampLookup: (gpid: string) => void;
  onOpenAssignment: (gpid: string) => void;
  onToggleJourney: (gpid: string) => void;
  isJourneyActive: boolean;
  isLoadingJourney: boolean;
  journeyTrail: JourneyBreadcrumb[] | null;
}

type TabKey = 'journey' | 'details' | 'route' | 'officers';

const TABS: { key: TabKey; label: string }[] = [
  { key: 'journey', label: 'Journey' },
  { key: 'details', label: 'Details' },
  { key: 'route', label: 'Route' },
  { key: 'officers', label: 'Officers' },
];

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

const CONNECTION_COLOR: Record<string, string> = {
  LIVE: 'var(--color-status-active)',
  DEGRADED: 'var(--color-status-warning)',
  OFFLINE: 'var(--color-status-critical)',
};

function InfoField({ label, value, mono, color }: { label: string; value: React.ReactNode; mono?: boolean; color?: string }) {
  return (
    <div>
      <span className="text-[10px] text-text-tertiary uppercase tracking-wide">{label}</span>
      <p className={`text-[12px] font-medium mt-0.5 ${mono ? 'mono' : ''}`} style={{ color: color || 'var(--color-text-primary)' }}>
        {value}
      </p>
    </div>
  );
}

function SectionCard({ icon: Icon, title, iconColor, children }: { icon: LucideIcon; title: string; iconColor?: string; children: React.ReactNode }) {
  return (
    <div className="p-3 bg-elevated rounded-lg border border-border-subtle space-y-2.5">
      <div className="text-[10px] font-semibold uppercase tracking-wider text-text-tertiary flex items-center gap-1.5">
        <Icon className="w-3.5 h-3.5" style={{ color: iconColor || 'var(--color-text-secondary)' }} />
        {title}
      </div>
      {children}
    </div>
  );
}

export const IdolDetailDrawer: React.FC<IdolDetailDrawerProps> = ({
  marker,
  isOpen,
  onClose,
  onOpenTimestampLookup,
  onOpenAssignment,
  onToggleJourney,
  isJourneyActive,
  isLoadingJourney,
  journeyTrail,
}) => {
  const [idolDetail, setIdolDetail] = useState<Idol | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabKey>('journey');
  const [journeyData, setJourneyData] = useState<any>(null);

  useEffect(() => {
    if (!marker?.gpid) {
      setIdolDetail(null);
      setJourneyData(null);
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

    fetchJourney(marker.gpid)
      .then(setJourneyData)
      .catch(() => setJourneyData(null));
  }, [marker?.gpid]);

  // Reset to the Journey tab whenever a new GPID is selected
  useEffect(() => {
    setActiveTab('journey');
  }, [marker?.gpid]);

  const routeStats = useMemo(() => {
    if (!journeyTrail || journeyTrail.length === 0) return null;
    const speeds = journeyTrail.map((p) => p.speed).filter((s): s is number => s !== null);
    return {
      totalPoints: journeyTrail.length,
      startTime: journeyTrail[0].recorded_at,
      endTime: journeyTrail[journeyTrail.length - 1].recorded_at,
      maxSpeed: speeds.length > 0 ? Math.max(...speeds) : null,
    };
  }, [journeyTrail]);

  if (!isOpen || !marker) return null;

  const stateColor = STATE_COLOR[marker.procession_state] || STATE_COLOR.NOT_STARTED;
  const heightColor =
    marker.height_classification === 'RED'
      ? '#EF4444'
      : marker.height_classification === 'YELLOW'
      ? '#F59E0B'
      : '#10B981';

  return (
    <aside className="w-96 bg-base border-l border-border-subtle flex flex-col h-full z-30 shadow-2xl overflow-hidden shrink-0">
      {/* Header */}
      <div className="p-4 border-b border-border-subtle flex items-start justify-between">
        <div className="min-w-0">
          <div className="text-[10px] font-semibold uppercase tracking-widest text-text-tertiary mb-0.5">
            Selected GPID
          </div>
          <div className="text-[15px] font-semibold text-text-primary mono truncate">
            {marker.gpid}
          </div>
          <div className="text-xs text-text-secondary truncate max-w-[280px] mt-0.5">
            {marker.idol_name}
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded text-text-tertiary hover:text-text-primary hover:bg-elevated transition-colors shrink-0"
          title="Close details"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Status & freshness ribbon */}
      <div className="px-4 py-2 border-b border-border-subtle flex items-center justify-between text-xs bg-elevated-1/50">
        <div className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: stateColor }} />
          <span className="text-[11px] font-medium uppercase tracking-wide" style={{ color: stateColor }}>
            {STATE_LABEL[marker.procession_state]}
          </span>
        </div>
        <div className="flex items-center gap-1.5 text-[11px] text-text-secondary">
          <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: CONNECTION_COLOR[marker.connection_state] }} />
          <span>Telemetry: <strong className="text-text-primary font-medium">{marker.connection_state}</strong></span>
        </div>
      </div>

      {/* Primary Operational Summary Card (Rule 14 & 15 & 16 & 17) */}
      <div className="p-3 mx-4 my-2.5 bg-elevated-1 border border-border-default/80 rounded-lg shadow-sm space-y-2">
        <div className="flex items-center justify-between pb-1.5 border-b border-border-subtle">
          <span className="text-[10px] font-bold uppercase tracking-wider text-accent">
            Operational Summary
          </span>
          <span
            className="text-[10px] font-bold px-2 py-0.5 rounded border"
            style={{
              color: heightColor,
              borderColor: `${heightColor}50`,
              backgroundColor: `${heightColor}15`,
            }}
          >
            {idolDetail?.idol_height || marker.idol_height ? `${idolDetail?.idol_height || marker.idol_height} ft` : '>=15 ft'} (
            {marker.height_classification === 'RED' ? '26+ FT' : marker.height_classification === 'YELLOW' ? '21–25 FT' : '15–20 FT'})
          </span>
        </div>

        <div className="grid grid-cols-2 gap-x-2.5 gap-y-2 text-[11px]">
          <div>
            <span className="text-[9px] uppercase tracking-wider text-text-tertiary">GPID</span>
            <p className="font-semibold text-text-primary mono truncate">{marker.gpid}</p>
          </div>
          <div>
            <span className="text-[9px] uppercase tracking-wider text-text-tertiary">Constable Assigned</span>
            <p className="font-medium text-text-primary truncate">
              {marker.assigned_constable ? `${marker.assigned_constable.name}` : 'Unassigned'}
            </p>
          </div>
          <div>
            <span className="text-[9px] uppercase tracking-wider text-text-tertiary">Origin Location</span>
            <p className="font-medium text-text-secondary truncate" title={idolDetail?.address || marker.origin_location || marker.police_station}>
              {idolDetail?.address || marker.origin_location || marker.police_station}
            </p>
          </div>
          <div>
            <span className="text-[9px] uppercase tracking-wider text-text-tertiary">Destination</span>
            <p className="font-medium text-text-secondary truncate" title={idolDetail?.river_name || marker.destination || 'Visarjan Waterbody'}>
              {idolDetail?.river_name || marker.destination || 'Visarjan Waterbody'}
            </p>
          </div>
          <div>
            <span className="text-[9px] uppercase tracking-wider text-text-tertiary">Owner / Mandap</span>
            <p className="font-medium text-text-primary truncate" title={idolDetail?.name || marker.owner_name || marker.idol_name}>
              {idolDetail?.name || marker.owner_name || marker.idol_name}
            </p>
          </div>
          <div>
            <span className="text-[9px] uppercase tracking-wider text-text-tertiary">Contact Number</span>
            <p className="font-medium text-text-secondary truncate">
              {idolDetail?.contact_info?.mobile_no
                ? idolDetail.contact_info.mobile_no
                : idolDetail
                ? 'Restricted / Authorized Only'
                : 'Loading…'}
            </p>
          </div>
          <div>
            <span className="text-[9px] uppercase tracking-wider text-text-tertiary">Origin Zone</span>
            <p className="font-medium text-text-secondary truncate">{idolDetail?.zone || marker.zone}</p>
          </div>
          <div>
            <span className="text-[9px] uppercase tracking-wider text-text-tertiary">Current Zone</span>
            <p className="font-medium text-text-secondary truncate">{marker.zone}</p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center border-b border-border-subtle px-4">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-3 py-2 text-[11px] font-medium uppercase tracking-wider border-b-2 -mb-px transition-colors ${
              activeTab === tab.key
                ? 'text-text-primary border-accent'
                : 'text-text-tertiary border-transparent hover:text-text-secondary'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 text-xs">
        {activeTab === 'journey' && (
          <div className="space-y-3">
            <button
              onClick={() => onToggleJourney(marker.gpid)}
              disabled={isLoadingJourney}
              className={`w-full p-2.5 rounded-md border text-left flex items-center gap-2 transition-colors ${
                isJourneyActive
                  ? 'bg-accent border-accent text-base font-medium'
                  : 'bg-elevated border-border-subtle text-text-secondary hover:border-border-default'
              }`}
            >
              <Navigation className="w-4 h-4 shrink-0" />
              <span className="font-medium text-[11px]">
                {isLoadingJourney ? 'Loading journey…' : isJourneyActive ? 'Hide journey path on map' : 'View recorded path on map'}
              </span>
            </button>

            {/* Travelled Distance Display (Rule 46) */}
            <div className="p-2.5 bg-elevated-1 border border-border-subtle rounded-md flex items-center justify-between text-[11px]">
              <span className="text-text-tertiary uppercase tracking-wider text-[10px] font-medium">Distance Travelled</span>
              <span className="font-semibold text-text-primary mono">
                {journeyData?.distance_travelled_km !== undefined && journeyData?.distance_travelled_km !== null
                  ? `${journeyData.distance_travelled_km} km`
                  : 'Distance unavailable'}
              </span>
            </div>

            {/* Operational Event Timeline (Rule 25 & 26) */}
            {journeyData?.events && journeyData.events.length > 0 && (
              <div className="p-2.5 bg-elevated-1 border border-border-subtle rounded-md space-y-2">
                <div className="text-[10px] text-accent font-semibold uppercase tracking-wider">
                  Operational Event History
                </div>
                <div className="relative pl-1 space-y-2">
                  {journeyData.events.map((ev: any, idx: number) => (
                    <div key={ev.id || idx} className="flex items-start gap-2.5 text-[11px]">
                      <span className="w-2 h-2 rounded-full bg-accent mt-1 shrink-0" />
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-text-primary">{ev.label || ev.event_type}</span>
                          <span className="mono text-[10px] text-text-tertiary">
                            {new Date(ev.timestamp).toLocaleTimeString()}
                          </span>
                        </div>
                        {ev.actor && (
                          <div className="text-[10px] text-text-secondary">By: {ev.actor}</div>
                        )}
                        {ev.zone && (
                          <div className="text-[10px] text-text-tertiary">Zone: {ev.zone}</div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {!journeyTrail && (
              <p className="text-text-tertiary text-center py-4">
                No recorded GPS trail loaded yet.
              </p>
            )}

            {journeyTrail && journeyTrail.length === 0 && (
              <p className="text-text-tertiary text-center py-4">
                No recorded GPS breadcrumbs found for this idol yet.
              </p>
            )}

            {journeyTrail && journeyTrail.length > 0 && (
              <div>
                <div className="text-[10px] text-text-tertiary uppercase tracking-wide mb-2">
                  Showing latest {Math.min(20, journeyTrail.length)} of {journeyTrail.length} recorded points
                </div>
                <div className="relative pl-1">
                  {journeyTrail
                    .slice(-20)
                    .reverse()
                    .map((p, i, arr) => (
                      <div key={p.recorded_at + i} className="flex items-start gap-3 relative">
                        <div className="flex flex-col items-center">
                          <span
                            className={`w-2.5 h-2.5 rounded-full shrink-0 mt-0.5 ${i === 0 ? 'bg-accent' : 'bg-status-active'}`}
                          />
                          {i < arr.length - 1 && <span className="w-px flex-1 bg-border-default" style={{ minHeight: '28px' }} />}
                        </div>
                        <div className="pb-3.5 min-w-0">
                          <div className="text-[12px] text-text-primary font-medium mono">
                            {new Date(p.recorded_at).toLocaleTimeString()}
                          </div>
                          <div className="text-[11px] text-text-secondary">
                            {p.speed !== null ? `${p.speed} km/h` : 'Stationary'}
                            {p.accuracy !== null ? ` · ±${p.accuracy}m accuracy` : ''}
                          </div>
                        </div>
                      </div>
                    ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'details' && (
          <div className="space-y-3">
            <SectionCard icon={MapPin} title="Current Position" iconColor="var(--color-status-tracking)">
              <div className="grid grid-cols-2 gap-2.5">
                <InfoField label="Latitude" value={marker.latitude.toFixed(6)} mono />
                <InfoField label="Longitude" value={marker.longitude.toFixed(6)} mono />
                <InfoField label="Speed" value={marker.speed !== null ? `${marker.speed} km/h` : 'Stationary'} />
                <InfoField label="GPS Accuracy" value={marker.accuracy !== null ? `±${marker.accuracy} m` : 'N/A'} />
              </div>
              <div className="text-[10px] text-text-tertiary pt-1 border-t border-border-subtle">
                Last fix: {new Date(marker.last_gps_timestamp).toLocaleString()}
              </div>
            </SectionCard>

            {loading && <div className="text-text-tertiary text-center py-2">Loading full idol master data…</div>}
            {error && <div className="text-status-critical text-center py-1">{error}</div>}
            {idolDetail && (
              <SectionCard icon={Layers} title="Idol & Pandal Specifications">
                <div className="grid grid-cols-2 gap-2.5">
                  <InfoField label="Association / Samithi" value={idolDetail.association_name || 'Individual'} />
                  <InfoField label="Idol Type" value={idolDetail.idol_type || 'Standard'} />
                  <InfoField label="Idol Height" value={idolDetail.idol_height ? `${idolDetail.idol_height} ft` : 'N/A'} />
                  <InfoField label="Pandal Height" value={idolDetail.pandal_height ? `${idolDetail.pandal_height} ft` : 'N/A'} />
                  <InfoField label="Destination Waterbody" value={idolDetail.river_name || 'Hussain Sagar'} color="var(--color-status-visarjan)" />
                  <InfoField label="Immersion Date" value={idolDetail.immersion_date || 'N/A'} />
                </div>
              </SectionCard>
            )}

            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => onOpenTimestampLookup(marker.gpid)}
                className="p-2.5 rounded-md border bg-elevated border-border-subtle text-text-secondary hover:border-border-default hover:text-text-primary text-left flex items-center gap-2 transition-colors"
              >
                <Clock className="w-4 h-4 shrink-0 text-status-warning" />
                <span className="font-medium text-[11px]">Timestamp Lookup</span>
              </button>
              <a
                href={getReportDownloadUrl(marker.gpid)}
                target="_blank"
                rel="noopener noreferrer"
                className="p-2.5 rounded-md border bg-elevated border-border-subtle text-text-secondary hover:border-border-default hover:text-text-primary text-left flex items-center gap-2 transition-colors"
              >
                <FileText className="w-4 h-4 shrink-0 text-status-visarjan" />
                <span className="font-medium text-[11px]">Official PDF</span>
              </a>
            </div>
          </div>
        )}

        {activeTab === 'route' && (
          <div className="space-y-3">
            <SectionCard icon={RouteIcon} title="Route Summary" iconColor="var(--color-accent)">
              {!routeStats ? (
                <p className="text-text-tertiary py-2">
                  Load the journey trail (Journey tab) to see route statistics.
                </p>
              ) : (
                <div className="grid grid-cols-2 gap-2.5">
                  <InfoField label="Recorded Points" value={routeStats.totalPoints} mono />
                  <InfoField label="Max Speed" value={routeStats.maxSpeed !== null ? `${routeStats.maxSpeed} km/h` : 'N/A'} />
                  <InfoField label="Trail Start" value={new Date(routeStats.startTime).toLocaleTimeString()} mono />
                  <InfoField label="Trail End" value={new Date(routeStats.endTime).toLocaleTimeString()} mono />
                </div>
              )}
            </SectionCard>

            <SectionCard icon={Layers} title="Jurisdiction" iconColor="var(--color-status-tracking)">
              <div className="grid grid-cols-2 gap-2.5">
                <InfoField label="Zone" value={marker.zone} />
                <InfoField label="Division" value={marker.division || 'N/A'} />
                <InfoField label="Police Station" value={marker.police_station} />
                <InfoField label="Station Code" value={marker.ps_code} mono color="var(--color-accent)" />
              </div>
            </SectionCard>
          </div>
        )}

        {activeTab === 'officers' && (
          <div className="space-y-3">
            <SectionCard icon={Shield} title="Assigned Ground Constable" iconColor="var(--color-status-active)">
              {marker.assigned_constable ? (
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-text-primary">{marker.assigned_constable.name}</span>
                    <span className="mono text-[11px] px-1.5 py-0.5 bg-elevated-2 text-text-secondary rounded border border-border-subtle">
                      ID: {marker.assigned_constable.police_id}
                    </span>
                  </div>
                  <div className="text-text-secondary text-[11px] flex items-center gap-1.5">
                    <Phone className="w-3 h-3 text-text-tertiary" />
                    <span>{marker.assigned_constable.phone_number || 'Mobile not provided'}</span>
                  </div>
                </div>
              ) : (
                <div className="flex items-center gap-2 text-status-warning bg-status-warning-soft p-2.5 rounded-md">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span className="text-[11px]">No ground constable currently assigned.</span>
                </div>
              )}
            </SectionCard>

            <button
              onClick={() => onOpenAssignment(marker.gpid)}
              className="w-full p-2.5 rounded-md border bg-elevated border-border-subtle text-text-secondary hover:border-border-default hover:text-text-primary text-left flex items-center gap-2 transition-colors"
            >
              <UserCheck className="w-4 h-4 shrink-0 text-status-active" />
              <span className="font-medium text-[11px]">
                {marker.assigned_constable ? 'Handover Duty' : 'Assign Constable'}
              </span>
            </button>
          </div>
        )}
      </div>
    </aside>
  );
};
