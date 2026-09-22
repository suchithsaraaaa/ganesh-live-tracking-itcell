import React, { useState, useEffect, useCallback } from 'react';
import { User, DashboardKPIs, ActiveMarker, TimestampLookupResult, JourneyBreadcrumb, Idol } from './types';
import { fetchCurrentUser, fetchDashboardData, fetchJourney } from './api/client';
import { Header } from './components/Header';
import { KpiCards } from './components/KpiCards';
import { SearchFilterBar } from './components/SearchFilterBar';
import { LiveMap } from './components/LiveMap';
import { IdolDetailDrawer } from './components/IdolDetailDrawer';
import { TimestampLookupModal } from './components/TimestampLookupModal';
import { AssignmentModal } from './components/AssignmentModal';
import { IdolTable } from './components/IdolTable';
import { Map, Table } from 'lucide-react';

export const App: React.FC = () => {
  // User & Auth
  const [currentUser, setCurrentUser] = useState<User | null>(null);

  // Operational Data
  const [kpis, setKpis] = useState<DashboardKPIs | null>(null);
  const [activeMarkers, setActiveMarkers] = useState<ActiveMarker[]>([]);
  const [selectedMarker, setSelectedMarker] = useState<ActiveMarker | null>(null);

  // Filters
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [selectedZone, setSelectedZone] = useState<string>('All Zones');
  const [selectedPs, setSelectedPs] = useState<string>('');
  const [selectedStateFilter, setSelectedStateFilter] = useState<string>('ALL');

  // UI Modes
  const [viewMode, setViewMode] = useState<'map' | 'split'>('map');
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  // Modals
  const [timestampModalOpen, setTimestampModalOpen] = useState<boolean>(false);
  const [targetGpidForLookup, setTargetGpidForLookup] = useState<string>('');
  const [assignmentModalOpen, setAssignmentModalOpen] = useState<boolean>(false);
  const [targetGpidForAssignment, setTargetGpidForAssignment] = useState<string>('');

  // Historical & Journey Overlays
  const [historicalLookup, setHistoricalLookup] = useState<TimestampLookupResult | null>(null);
  const [journeyTrail, setJourneyTrail] = useState<JourneyBreadcrumb[] | null>(null);
  const [isLoadingJourney, setIsLoadingJourney] = useState<boolean>(false);

  // Initial user fetch
  useEffect(() => {
    fetchCurrentUser().then((user) => {
      setCurrentUser(user);
    });
  }, []);

  // Fetch Dashboard Telemetry & Active Markers
  const loadDashboard = useCallback(async (showSpin: boolean = false) => {
    if (showSpin) setIsRefreshing(true);
    try {
      const data = await fetchDashboardData({
        zone: selectedZone !== 'All Zones' ? selectedZone : undefined,
        police_station: selectedPs || undefined,
      });
      setKpis(data.kpis);
      setActiveMarkers(data.active_markers);
      setLastUpdated(new Date());

      // If a marker is selected, refresh its live state
      setSelectedMarker((prev) => {
        if (!prev) return null;
        const updated = data.active_markers.find((m) => m.gpid === prev.gpid);
        return updated || prev;
      });
    } catch (err) {
      console.error('Failed to load dashboard:', err);
    } finally {
      if (showSpin) setIsRefreshing(false);
    }
  }, [selectedZone, selectedPs]);

  // Polling loop: 10s interval (no WebSockets needed for MVP)
  useEffect(() => {
    loadDashboard(true);
    const interval = setInterval(() => {
      loadDashboard(false);
    }, 10000);
    return () => clearInterval(interval);
  }, [loadDashboard]);

  // Handle marker selection on map
  const handleSelectMarker = (marker: ActiveMarker) => {
    setSelectedMarker(marker);
    setIsDrawerOpen(true);
    setHistoricalLookup(null);
  };

  // Clear selection (restores all map markers)
  const handleClearSelection = () => {
    setSelectedMarker(null);
    setIsDrawerOpen(false);
    setJourneyTrail(null);
    setHistoricalLookup(null);
  };

  // Handle selecting an idol from table
  const handleSelectIdolFromTable = (idol: Idol) => {
    // Check if it exists in active markers
    const existing = activeMarkers.find((m) => m.gpid === idol.gpid);
    if (existing) {
      setSelectedMarker(existing);
    } else {
      // Create representative marker with station fallback coordinates (Hyderabad approx)
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
  };

  // Journey Trail toggle
  const handleToggleJourney = async (gpid: string) => {
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
  };

  // Open Timestamp Lookup Modal
  const handleOpenTimestampLookup = (gpid: string) => {
    setTargetGpidForLookup(gpid);
    setTimestampModalOpen(true);
  };

  // Open Assignment Modal
  const handleOpenAssignment = (gpid: string) => {
    setTargetGpidForAssignment(gpid);
    setAssignmentModalOpen(true);
  };

  // Filter markers by active search or state
  const filteredMarkers = activeMarkers.filter((m) => {
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
    return true;
  });

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-slate-950 text-slate-100">
      {/* Top Police Command Header */}
      <Header
        user={currentUser}
        lastUpdated={lastUpdated}
        isRefreshing={isRefreshing}
        onRefresh={() => loadDashboard(true)}
      />

      {/* High-Level Operational Metrics / KPIs */}
      <KpiCards
        kpis={kpis}
        selectedStateFilter={selectedStateFilter}
        onSelectStateFilter={setSelectedStateFilter}
      />

      {/* Filter and Search Bar */}
      <div className="flex items-center justify-between bg-slate-900 border-b border-slate-800 pr-3">
        <div className="flex-1">
          <SearchFilterBar
            searchTerm={searchTerm}
            onSearchChange={setSearchTerm}
            selectedZone={selectedZone}
            onZoneChange={setSelectedZone}
            selectedPs={selectedPs}
            onPsChange={setSelectedPs}
            onClear={() => {
              setSearchTerm('');
              setSelectedZone('All Zones');
              setSelectedPs('');
              setSelectedStateFilter('ALL');
            }}
          />
        </div>

        {/* View Toggle: Map vs Split */}
        <div className="flex items-center space-x-1 bg-slate-950 p-1 rounded border border-slate-800 text-xs shrink-0 ml-2">
          <button
            onClick={() => setViewMode('map')}
            className={`px-2.5 py-1 rounded flex items-center space-x-1.5 transition-colors ${
              viewMode === 'map'
                ? 'bg-blue-600 text-white font-semibold'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Map className="w-3.5 h-3.5" />
            <span>Map Only</span>
          </button>
          <button
            onClick={() => setViewMode('split')}
            className={`px-2.5 py-1 rounded flex items-center space-x-1.5 transition-colors ${
              viewMode === 'split'
                ? 'bg-blue-600 text-white font-semibold'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Table className="w-3.5 h-3.5" />
            <span>Map + Registry</span>
          </button>
        </div>
      </div>

      {/* Main Tactical Display Area */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Left Side: Map & Optional Split Table */}
        <div className="flex-1 flex flex-col h-full overflow-hidden">
          {/* Live Map */}
          <div className={viewMode === 'split' ? 'h-3/5 w-full relative' : 'h-full w-full relative'}>
            <LiveMap
              markers={filteredMarkers}
              selectedMarker={selectedMarker}
              onSelectMarker={handleSelectMarker}
              onClearSelection={handleClearSelection}
              historicalLookup={historicalLookup}
              journeyTrail={journeyTrail}
            />
          </div>

          {/* Registry Split View */}
          {viewMode === 'split' && (
            <div className="h-2/5 w-full">
              <IdolTable
                searchTerm={searchTerm}
                selectedZone={selectedZone}
                selectedPs={selectedPs}
                selectedStateFilter={selectedStateFilter}
                selectedGpid={selectedMarker?.gpid || null}
                onSelectIdol={handleSelectIdolFromTable}
              />
            </div>
          )}
        </div>

        {/* Right Side: Selected Idol Detail Drawer */}
        <IdolDetailDrawer
          marker={selectedMarker}
          isOpen={isDrawerOpen}
          onClose={handleClearSelection}
          onOpenTimestampLookup={handleOpenTimestampLookup}
          onOpenAssignment={handleOpenAssignment}
          onToggleJourney={handleToggleJourney}
          isJourneyActive={Boolean(journeyTrail)}
          isLoadingJourney={isLoadingJourney}
        />
      </div>

      {/* Timestamp Lookup Modal */}
      <TimestampLookupModal
        isOpen={timestampModalOpen}
        initialGpid={targetGpidForLookup}
        onClose={() => setTimestampModalOpen(false)}
        onPlotPoint={(result) => setHistoricalLookup(result)}
      />

      {/* Assignment & Handover Modal */}
      <AssignmentModal
        isOpen={assignmentModalOpen}
        gpid={targetGpidForAssignment}
        currentAssignmentId={null}
        currentConstableName={selectedMarker?.assigned_constable?.name}
        onClose={() => setAssignmentModalOpen(false)}
        onSuccess={() => {
          loadDashboard(true);
        }}
      />
    </div>
  );
};
