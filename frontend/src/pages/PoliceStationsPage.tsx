import React, { useMemo, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Building2, Search, Filter, Loader2 } from 'lucide-react';
import { useTracking } from '../context/TrackingContext';
import { useAssignments } from '../hooks/useAssignments';
import { fetchAuthoritativePoliceStations } from '../api/client';
import { PoliceStationMaster } from '../types';
import { EmptyState } from '../components/shared/States';

interface StationRow {
  station: string;
  code: string;
  zone: string;
  division: string;
  hasBoundary: boolean;
  total: number;
  moving: number;
  holding: number;
  immersed: number;
  activeOfficers: number;
}

export const PoliceStationsPage: React.FC = () => {
  const { activeMarkers, setSelectedPs } = useTracking();
  const { assignments } = useAssignments();
  const [search, setSearch] = useState('');
  const [selectedZone, setSelectedZone] = useState<string>('ALL');
  const [masterStations, setMasterStations] = useState<PoliceStationMaster[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const navigate = useNavigate();

  useEffect(() => {
    let mounted = true;
    fetchAuthoritativePoliceStations()
      .then((data) => {
        if (mounted) setMasterStations(data.results || []);
      })
      .catch((err) => {
        console.error('Failed to load authoritative police stations:', err);
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const zones = useMemo(() => {
    const set = new Set<string>();
    masterStations.forEach((s) => {
      if (s.zone) set.add(s.zone);
    });
    return Array.from(set).sort();
  }, [masterStations]);

  const rows: StationRow[] = useMemo(() => {
    const stationMap = new Map<string, StationRow>();

    // Seed with authoritative master stations
    masterStations.forEach((ms) => {
      const stationName = ms.ps_name || ms.name || '';
      const stationCode = ms.ps_code || ms.code || '';
      stationMap.set(stationName.toUpperCase(), {
        station: stationName,
        code: stationCode,
        zone: ms.zone,
        division: ms.division,
        hasBoundary: Boolean(ms.has_boundary_polygon),
        total: 0,
        moving: 0,
        holding: 0,
        immersed: 0,
        activeOfficers: 0,
      });
    });

    // Aggregate active telemetry
    activeMarkers.forEach((m) => {
      const psName = (m.police_station || 'Unassigned').toUpperCase();
      let row = stationMap.get(psName);
      if (!row) {
        row = {
          station: m.police_station || 'Unassigned',
          code: '',
          zone: m.zone || '',
          division: '',
          hasBoundary: false,
          total: 0,
          moving: 0,
          holding: 0,
          immersed: 0,
          activeOfficers: 0,
        };
        stationMap.set(psName, row);
      }
      row.total += 1;
      if (m.procession_state === 'MOVING') row.moving += 1;
      if (m.procession_state === 'HOLDING') row.holding += 1;
      if (m.procession_state === 'IMMERSION_COMPLETED') row.immersed += 1;
    });

    // Aggregate active assignments
    assignments.forEach((a) => {
      if (!a.is_active) return;
      const psName = (a.police_station || 'Unassigned').toUpperCase();
      const row = stationMap.get(psName);
      if (row) {
        row.activeOfficers += 1;
      }
    });

    const list = Array.from(stationMap.values());

    return list.filter((r) => {
      const matchSearch =
        !search ||
        r.station.toLowerCase().includes(search.toLowerCase()) ||
        r.code.toLowerCase().includes(search.toLowerCase()) ||
        r.division.toLowerCase().includes(search.toLowerCase());
      const matchZone = selectedZone === 'ALL' || r.zone === selectedZone;
      return matchSearch && matchZone;
    }).sort((a, b) => {
      // Show stations with active idols first, then alphabetically
      if (b.total !== a.total) return b.total - a.total;
      return a.station.localeCompare(b.station);
    });
  }, [masterStations, activeMarkers, assignments, search, selectedZone]);

  const openInLiveMap = (station: string) => {
    setSelectedPs(station);
    navigate('/live-map');
  };

  return (
    <div className="h-full flex flex-col overflow-hidden animate-fade-in-up">
      <div className="px-6 pt-6 pb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-lg font-semibold text-text-primary">Police Stations</h1>
            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-accent/15 text-accent border border-accent/25 mono">
              72 Authoritative Stations
            </span>
          </div>
          <p className="text-xs text-text-tertiary mt-0.5">
            Authoritative Hyderabad Police jurisdiction stations with live GPID telemetry and officer assignments.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          {/* Zone filter */}
          {zones.length > 0 && (
            <div className="relative">
              <select
                value={selectedZone}
                onChange={(e) => setSelectedZone(e.target.value)}
                aria-label="Filter by Zone"
                className="pl-3 pr-8 py-2 bg-elevated-2 border border-border-default rounded-md text-text-primary text-xs focus:outline-none focus:border-accent appearance-none cursor-pointer"
              >
                <option value="ALL">All Zones ({zones.length})</option>
                {zones.map((z) => (
                  <option key={z} value={z}>
                    {z}
                  </option>
                ))}
              </select>
              <Filter className="w-3 h-3 absolute right-2.5 top-1/2 -translate-y-1/2 text-text-tertiary pointer-events-none" />
            </div>
          )}

          {/* Search */}
          <div className="relative w-64">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-text-tertiary" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search station or code…"
              className="w-full pl-8 pr-3 py-2 bg-elevated-2 border border-border-default rounded-md text-text-primary text-xs focus:outline-none focus:border-accent"
            />
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-6 pb-6">
        {loading ? (
          <div className="h-48 flex items-center justify-center space-x-2 text-text-tertiary">
            <Loader2 className="w-5 h-5 animate-spin text-accent" />
            <span className="text-xs">Loading authoritative police station registry...</span>
          </div>
        ) : rows.length === 0 ? (
          <EmptyState title="No matching police stations" hint="Try adjusting your zone or search filter." />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {rows.map((r) => (
              <button
                key={r.station}
                onClick={() => openInLiveMap(r.station)}
                className="text-left bg-elevated border border-border-subtle hover:border-accent/40 rounded-lg p-4 transition-colors cursor-pointer group"
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2 min-w-0">
                    <Building2 className="w-4 h-4 text-accent shrink-0 group-hover:scale-110 transition-transform" strokeWidth={1.8} />
                    <div className="min-w-0">
                      <div className="flex items-center space-x-1.5">
                        <span className="text-sm font-semibold text-text-primary truncate">{r.station}</span>
                        {r.code && (
                          <span className="text-[10px] px-1 py-0.2 rounded bg-elevated-2 text-text-tertiary mono">
                            {r.code}
                          </span>
                        )}
                      </div>
                      {r.division && (
                        <div className="text-[10px] text-text-tertiary truncate">
                          Div: {r.division}
                        </div>
                      )}
                    </div>
                  </div>
                  {r.zone && (
                    <span className="text-[10px] text-text-tertiary bg-elevated-2 px-2 py-0.5 rounded border border-border-subtle shrink-0">
                      {r.zone}
                    </span>
                  )}
                </div>
                <div className="grid grid-cols-4 gap-2 text-center bg-base/50 p-2 rounded-md border border-border-subtle">
                  <div>
                    <div className="text-sm font-semibold text-text-primary mono">{r.total}</div>
                    <div className="text-[9px] uppercase text-text-tertiary tracking-wide">Live Idols</div>
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-status-active mono">{r.moving}</div>
                    <div className="text-[9px] uppercase text-text-tertiary tracking-wide">Moving</div>
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-status-warning mono">{r.holding}</div>
                    <div className="text-[9px] uppercase text-text-tertiary tracking-wide">Holding</div>
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-text-secondary mono">{r.activeOfficers}</div>
                    <div className="text-[9px] uppercase text-text-tertiary tracking-wide">Officers</div>
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
