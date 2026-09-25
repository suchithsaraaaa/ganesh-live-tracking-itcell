import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { DashboardKPIs, ActiveMarker, TimestampLookupResult, JourneyBreadcrumb, Idol } from '../types';
import { fetchDashboardData, fetchJourney } from '../api/client';

interface TrackingContextValue {
  kpis: DashboardKPIs | null;
  activeMarkers: ActiveMarker[];
  filteredMarkers: ActiveMarker[];
  isRefreshing: boolean;
  lastUpdated: Date | null;

  searchTerm: string;
  setSearchTerm: (v: string) => void;
  selectedZone: string;
  setSelectedZone: (v: string) => void;
  selectedPs: string;
  setSelectedPs: (v: string) => void;
  selectedStateFilter: string;
  setSelectedStateFilter: (v: string) => void;
  selectedHeightBucket: string;
  setSelectedHeightBucket: (v: string) => void;
  isImmersionsToday: boolean;
  setIsImmersionsToday: (v: boolean) => void;
  clearFilters: () => void;

  selectedMarker: ActiveMarker | null;
  isDrawerOpen: boolean;
  handleSelectMarker: (marker: ActiveMarker) => void;
  handleSelectIdol: (idol: Idol) => void;
  handleClearSelection: () => void;

  historicalLookup: TimestampLookupResult | null;
  setHistoricalLookup: (v: TimestampLookupResult | null) => void;
  journeyTrail: JourneyBreadcrumb[] | null;
  isLoadingJourney: boolean;
  handleToggleJourney: (gpid: string) => Promise<void>;

  timestampModalOpen: boolean;
  targetGpidForLookup: string;
  openTimestampLookup: (gpid: string) => void;
  closeTimestampLookup: () => void;

  assignmentModalOpen: boolean;
  targetGpidForAssignment: string;
  openAssignment: (gpid: string) => void;
  closeAssignment: () => void;

  loadDashboard: (showSpin?: boolean) => Promise<void>;

  /** Call on mount from pages that need live dashboard polling (Dashboard, LiveMap, etc.) */
  activatePolling: () => void;
  /** Call on unmount to decrement the polling subscriber count */
  deactivatePolling: () => void;
}

const TrackingContext = createContext<TrackingContextValue | undefined>(undefined);

/** Dashboard polling interval in milliseconds */
const DASHBOARD_POLL_INTERVAL_MS = 10_000;

export const TrackingProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [kpis, setKpis] = useState<DashboardKPIs | null>(null);
  const [activeMarkers, setActiveMarkers] = useState<ActiveMarker[]>([]);
  const [selectedMarker, setSelectedMarker] = useState<ActiveMarker | null>(null);

  const [searchTerm, setSearchTerm] = useState('');
  const [selectedZone, setSelectedZone] = useState('All Zones');
  const [selectedPs, setSelectedPs] = useState('');
  const [selectedStateFilter, setSelectedStateFilter] = useState('ALL');
  const [selectedHeightBucket, setSelectedHeightBucket] = useState('ALL');
  const [isImmersionsToday, setIsImmersionsToday] = useState(false);

  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const [timestampModalOpen, setTimestampModalOpen] = useState(false);
  const [targetGpidForLookup, setTargetGpidForLookup] = useState('');
  const [assignmentModalOpen, setAssignmentModalOpen] = useState(false);
  const [targetGpidForAssignment, setTargetGpidForAssignment] = useState('');

  const [historicalLookup, setHistoricalLookup] = useState<TimestampLookupResult | null>(null);
  const [journeyTrail, setJourneyTrail] = useState<JourneyBreadcrumb[] | null>(null);
  const [isLoadingJourney, setIsLoadingJourney] = useState(false);

  // Polling subscriber ref-count: only poll when > 0 pages need live data
  const pollingSubscribersRef = useRef(0);
  const [pollingActive, setPollingActive] = useState(false);

  const activatePolling = useCallback(() => {
    pollingSubscribersRef.current += 1;
    setPollingActive(true);
  }, []);

  const deactivatePolling = useCallback(() => {
    pollingSubscribersRef.current = Math.max(0, pollingSubscribersRef.current - 1);
    if (pollingSubscribersRef.current === 0) {
      setPollingActive(false);
    }
  }, []);

  const loadDashboard = useCallback(async (showSpin: boolean = false) => {
    if (showSpin) setIsRefreshing(true);
    try {
      const data = await fetchDashboardData({
        zone: selectedZone !== 'All Zones' ? selectedZone : undefined,
        police_station: selectedPs || undefined,
        height_bucket: selectedHeightBucket !== 'ALL' ? selectedHeightBucket : undefined,
        immersions_today: isImmersionsToday ? true : undefined,
      });
      setKpis(data.kpis);

      // Deduplicate markers by GPID to guarantee ONE GPID = ONE MARKER
      const uniqueMarkers: ActiveMarker[] = [];
      const seen = new Set<string>();
      for (const m of data.active_markers) {
        if (!seen.has(m.gpid)) {
          seen.add(m.gpid);
          uniqueMarkers.push(m);
        }
      }

      setActiveMarkers(uniqueMarkers);
      setLastUpdated(new Date());
      setSelectedMarker((prev) => {
        if (!prev) return null;
        const updated = uniqueMarkers.find((m) => m.gpid === prev.gpid);
        return updated || prev;
      });
    } catch (err) {
      console.error('Failed to load dashboard:', err);
    } finally {
      if (showSpin) setIsRefreshing(false);
    }
  }, [selectedZone, selectedPs, selectedHeightBucket, isImmersionsToday]);

  // Conditional polling: only runs when pollingActive is true AND tab is visible
  useEffect(() => {
    if (!pollingActive) return;

    // Initial fetch when polling activates
    loadDashboard(true);

    const tick = () => {
      // Skip polling when tab is hidden to avoid wasting bandwidth
      if (!document.hidden) {
        loadDashboard(false);
      }
    };

    const interval = setInterval(tick, DASHBOARD_POLL_INTERVAL_MS);

    const onVisibilityChange = () => {
      if (!document.hidden) {
        loadDashboard(false);
      }
    };
    document.addEventListener('visibilitychange', onVisibilityChange);

    return () => {
      clearInterval(interval);
      document.removeEventListener('visibilitychange', onVisibilityChange);
    };
  }, [pollingActive, loadDashboard]);

  const handleSelectMarker = useCallback((marker: ActiveMarker) => {
    setSelectedMarker(marker);
    setIsDrawerOpen(true);
    setHistoricalLookup(null);
  }, []);

  const handleClearSelection = useCallback(() => {
    setSelectedMarker(null);
    setIsDrawerOpen(false);
    setJourneyTrail(null);
    setHistoricalLookup(null);
  }, []);

  const handleSelectIdol = useCallback((idol: Idol) => {
    const existing = activeMarkers.find((m) => m.gpid === idol.gpid);
    if (existing) {
      setSelectedMarker(existing);
    } else {
      const heightVal = idol.idol_height ? Number(idol.idol_height) : null;
      const heightCat =
        heightVal && heightVal >= 26
          ? 'RED'
          : heightVal && heightVal >= 21
          ? 'YELLOW'
          : heightVal && heightVal >= 15
          ? 'GREEN'
          : 'SUBTHRESHOLD';

      if (idol.latitude && idol.longitude) {
        const syntheticMarker: ActiveMarker = {
          id: idol.id,
          gpid: idol.gpid,
          idol_name: idol.name || idol.association_name || 'Idol',
          association_name: idol.association_name,
          zone: idol.zone,
          division: idol.division,
          police_station: idol.police_station,
          ps_code: idol.ps_code,
          procession_state: idol.procession_state,
          connection_state: 'OFFLINE',
          is_origin_marker: true,
          latitude: Number(idol.latitude),
          longitude: Number(idol.longitude),
          speed: null,
          heading: null,
          accuracy: null,
          last_gps_timestamp: idol.updated_at,
          idol_height: heightVal,
          height_classification: heightCat,
          immersion_date: idol.immersion_date,
          origin_location: idol.address,
          destination: idol.river_name || idol.lake_type,
          owner_name: idol.name,
          assigned_constable: null,
        };
        setSelectedMarker(syntheticMarker);
      } else {
        setSelectedMarker(null);
      }
    }
    setIsDrawerOpen(true);
  }, [activeMarkers]);


  const handleToggleJourney = useCallback(async (gpid: string) => {
    if (journeyTrail) {
      setJourneyTrail(null);
      return;
    }
    setIsLoadingJourney(true);
    try {
      const data = await fetchJourney(gpid);
      setJourneyTrail(data.points);
    } catch (err) {
      alert('No recorded journey breadcrumbs found for this idol yet.');
    } finally {
      setIsLoadingJourney(false);
    }
  }, [journeyTrail]);

  const clearFilters = useCallback(() => {
    setSearchTerm('');
    setSelectedZone('All Zones');
    setSelectedPs('');
    setSelectedStateFilter('ALL');
    setSelectedHeightBucket('ALL');
    setIsImmersionsToday(false);
  }, []);

  const openTimestampLookup = useCallback((gpid: string) => {
    setTargetGpidForLookup(gpid);
    setTimestampModalOpen(true);
  }, []);
  const closeTimestampLookup = useCallback(() => setTimestampModalOpen(false), []);

  const openAssignment = useCallback((gpid: string) => {
    setTargetGpidForAssignment(gpid);
    setAssignmentModalOpen(true);
  }, []);
  const closeAssignment = useCallback(() => setAssignmentModalOpen(false), []);

  const filteredMarkers = useMemo(() => activeMarkers.filter((m) => {
    if (searchTerm) {
      const q = searchTerm.toLowerCase();
      const matches =
        m.gpid.toLowerCase().includes(q) ||
        m.idol_name.toLowerCase().includes(q) ||
        m.police_station.toLowerCase().includes(q);
      if (!matches) return false;
    }
    if (selectedStateFilter !== 'ALL') {
      if (selectedStateFilter === 'TRACKING_ACTIVE' && m.procession_state === 'NOT_STARTED') return false;
      if (selectedStateFilter === 'DEGRADED_OFFLINE' && m.connection_state === 'LIVE') return false;
      if (selectedStateFilter === 'MOVING' && m.procession_state !== 'MOVING') return false;
      if (selectedStateFilter === 'HOLDING' && m.procession_state !== 'HOLDING') return false;
      if (selectedStateFilter === 'AT_VISARJAN' && m.procession_state !== 'AT_VISARJAN') return false;
      if (selectedStateFilter === 'IMMERSION_COMPLETED' && m.procession_state !== 'IMMERSION_COMPLETED') return false;
    }
    if (selectedHeightBucket !== 'ALL') {
      if (selectedHeightBucket === 'below_15' && m.height_classification !== 'SUBTHRESHOLD') return false;
      if (selectedHeightBucket === '15_20' && m.height_classification !== 'GREEN') return false;
      if (selectedHeightBucket === '21_25' && m.height_classification !== 'YELLOW') return false;
      if (selectedHeightBucket === 'above_25' && m.height_classification !== 'RED') return false;
    }
    return true;
  }), [activeMarkers, searchTerm, selectedStateFilter, selectedHeightBucket]);

  const value: TrackingContextValue = {
    kpis, activeMarkers, filteredMarkers, isRefreshing, lastUpdated,
    searchTerm, setSearchTerm, selectedZone, setSelectedZone, selectedPs, setSelectedPs,
    selectedStateFilter, setSelectedStateFilter,
    selectedHeightBucket, setSelectedHeightBucket,
    isImmersionsToday, setIsImmersionsToday,
    clearFilters,
    selectedMarker, isDrawerOpen, handleSelectMarker, handleSelectIdol, handleClearSelection,
    historicalLookup, setHistoricalLookup, journeyTrail, isLoadingJourney, handleToggleJourney,
    timestampModalOpen, targetGpidForLookup, openTimestampLookup, closeTimestampLookup,
    assignmentModalOpen, targetGpidForAssignment, openAssignment, closeAssignment,
    loadDashboard, activatePolling, deactivatePolling,
  };

  return <TrackingContext.Provider value={value}>{children}</TrackingContext.Provider>;
};

export function useTracking(): TrackingContextValue {
  const ctx = useContext(TrackingContext);
  if (!ctx) throw new Error('useTracking must be used within a TrackingProvider');
  return ctx;
}
