import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
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
}

const TrackingContext = createContext<TrackingContextValue | undefined>(undefined);

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

  useEffect(() => {
    loadDashboard(true);
    const interval = setInterval(() => loadDashboard(false), 10000);
    return () => clearInterval(interval);
  }, [loadDashboard]);

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
      const syntheticMarker: ActiveMarker = {
        id: idol.id,
        gpid: idol.gpid,
        idol_name: idol.name,
        association_name: idol.association_name,
        zone: idol.zone,
        division: idol.division,
        police_station: idol.police_station,
        ps_code: idol.ps_code,
        procession_state: idol.procession_state,
        connection_state: 'OFFLINE',
        latitude: 17.3850,
        longitude: 78.4867,
        speed: null,
        heading: null,
        accuracy: null,
        last_gps_timestamp: idol.updated_at,
        assigned_constable: null,
      };
      setSelectedMarker(syntheticMarker);
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
    loadDashboard,
  };

  return <TrackingContext.Provider value={value}>{children}</TrackingContext.Provider>;
};

export function useTracking(): TrackingContextValue {
  const ctx = useContext(TrackingContext);
  if (!ctx) throw new Error('useTracking must be used within a TrackingProvider');
  return ctx;
}
