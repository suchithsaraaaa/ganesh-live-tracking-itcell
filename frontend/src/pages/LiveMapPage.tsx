import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Map, Table } from 'lucide-react';
import { useTracking } from '../context/TrackingContext';
import { SearchFilterBar } from '../components/SearchFilterBar';
import { LiveMap } from '../components/LiveMap';
import { IdolTable } from '../components/IdolTable';
import { fetchActiveTrackingMarkers, fetchJourney } from '../api/client';
import { ActiveMarker, JourneyBreadcrumb } from '../types';

export const LiveMapPage: React.FC = () => {
  const {
    searchTerm, setSearchTerm,
    selectedZone, setSelectedZone,
    selectedPs, setSelectedPs,
    selectedHeightBucket, setSelectedHeightBucket,
    isImmersionsToday, setIsImmersionsToday,
    clearFilters,
    selectedStateFilter,
    handleSelectIdol,
    handleSelectMarker: openDrawerForMarker,
    handleClearSelection: clearDrawerSelection,
    historicalLookup,
  } = useTracking();

  const [viewMode, setViewMode] = useState<'map' | 'split'>('map');
  const [activeMarkers, setActiveMarkers] = useState<ActiveMarker[]>([]);
  const [selectedMarker, setSelectedMarker] = useState<ActiveMarker | null>(null);
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null);
  const [journeyTrail, setJourneyTrail] = useState<JourneyBreadcrumb[] | null>(null);

  const selectedSessionIdRef = useRef<number | null>(null);
  selectedSessionIdRef.current = selectedSessionId;


  // Poll Active Processions every 3 seconds strictly from /api/v1/tracking/active/
  const pollActive = useCallback(async () => {
    try {
      const markers = await fetchActiveTrackingMarkers({
        zone: selectedZone !== 'All Zones' ? selectedZone : undefined,
        police_station: selectedPs || undefined,
        height_bucket: selectedHeightBucket !== 'ALL' ? selectedHeightBucket : undefined,
        search: searchTerm.trim() || undefined,
      });

      setActiveMarkers(markers);

      // Real-time update for selected procession & route extension
      const currentSessId = selectedSessionIdRef.current;
      if (currentSessId) {
        const matching = markers.find((m) => m.tracking_session_id === currentSessId);
        if (!matching) {
          // Procession was stopped: remove route and clear selection
          setSelectedMarker(null);
          setSelectedSessionId(null);
          selectedSessionIdRef.current = null;
          setJourneyTrail(null);
          clearDrawerSelection();
        } else {
          // In-place marker coordinate update
          setSelectedMarker(matching);

          // Append new GPS point to selected route if new coordinates/timestamp arrived
          setJourneyTrail((prevTrail) => {
            if (!prevTrail || prevTrail.length === 0) return prevTrail;
            const lastPt = prevTrail[prevTrail.length - 1];
            const isDifferentPos =
              Math.abs(lastPt.latitude - matching.latitude) > 1e-6 ||
              Math.abs(lastPt.longitude - matching.longitude) > 1e-6;
            const isDifferentTime = matching.last_gps_timestamp && lastPt.recorded_at !== matching.last_gps_timestamp;

            if (isDifferentPos || isDifferentTime) {
              return [
                ...prevTrail,
                {
                  latitude: matching.latitude,
                  longitude: matching.longitude,
                  speed: matching.speed,
                  heading: matching.heading,
                  accuracy: matching.accuracy,
                  recorded_at: matching.last_gps_timestamp,
                },
              ];
            }
            return prevTrail;
          });
        }
      }
    } catch (err) {
      console.error('Failed to poll active tracking sessions:', err);
    }
  }, [selectedZone, selectedPs, selectedHeightBucket, searchTerm, clearDrawerSelection]);

  useEffect(() => {
    pollActive();
    const interval = setInterval(pollActive, 3000);
    return () => clearInterval(interval);
  }, [pollActive]);


  // Handle live marker selection: load that exact session's historical telemetry
  const handleSelectActiveMarker = useCallback(
    async (marker: ActiveMarker) => {
      setSelectedMarker(marker);
      const sessId = marker.tracking_session_id || null;
      setSelectedSessionId(sessId);
      selectedSessionIdRef.current = sessId;

      openDrawerForMarker(marker);

      if (sessId) {
        try {
          const journeyData = await fetchJourney(marker.gpid, sessId);
          setJourneyTrail(journeyData.points || []);
        } catch (err) {
          console.error(`Failed to fetch journey for session ${sessId}:`, err);
          setJourneyTrail([]);
        }
      } else {
        setJourneyTrail([]);
      }
    },
    [openDrawerForMarker]
  );

  // Handle deselect: hide route while all active live markers remain visible
  const handleClearMarkerSelection = useCallback(() => {
    setSelectedMarker(null);
    setSelectedSessionId(null);
    selectedSessionIdRef.current = null;
    setJourneyTrail(null);
    clearDrawerSelection();
  }, [clearDrawerSelection]);

  return (
    <div className="h-full flex flex-col overflow-hidden animate-fade-in-up">
      <div className="flex items-center justify-between glass border-b pr-4">
        <div className="flex-1">
          <SearchFilterBar
            searchTerm={searchTerm}
            onSearchChange={setSearchTerm}
            selectedZone={selectedZone}
            onZoneChange={setSelectedZone}
            selectedPs={selectedPs}
            onPsChange={setSelectedPs}
            selectedHeightBucket={selectedHeightBucket}
            onHeightBucketChange={setSelectedHeightBucket}
            isImmersionsToday={isImmersionsToday}
            onImmersionsTodayChange={setIsImmersionsToday}
            onClear={clearFilters}
          />
        </div>

        <div className="flex items-center space-x-3 shrink-0 ml-2">
          {/* Active Procession Count Status */}
          <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-elevated border border-border-default text-xs">
            <span
              className={`w-2 h-2 rounded-full ${
                activeMarkers.length > 0 ? 'bg-status-active animate-pulse' : 'bg-text-tertiary'
              }`}
            />
            <span className="font-semibold text-text-primary mono">
              {activeMarkers.length}
            </span>
            <span className="text-[11px] text-text-secondary">
              Active Processions
            </span>
          </div>

          <div className="flex items-center space-x-1 bg-elevated-2 p-1 rounded-md border border-border-default text-xs">
            <button
              onClick={() => setViewMode('map')}
              className={`px-2.5 py-1.5 rounded flex items-center space-x-1.5 transition-colors ${
                viewMode === 'map' ? 'bg-accent text-base font-medium' : 'text-text-secondary hover:text-text-primary'
              }`}
            >
              <Map className="w-3.5 h-3.5" />
              <span>Map Only</span>
            </button>
            <button
              onClick={() => setViewMode('split')}
              className={`px-2.5 py-1.5 rounded flex items-center space-x-1.5 transition-colors ${
                viewMode === 'split' ? 'bg-accent text-base font-medium' : 'text-text-secondary hover:text-text-primary'
              }`}
            >
              <Table className="w-3.5 h-3.5" />
              <span>Map + Registry</span>
            </button>
          </div>
        </div>
      </div>

      <div className={viewMode === 'split' ? 'h-3/5 w-full relative' : 'h-full w-full relative'}>
        <LiveMap
          markers={activeMarkers}
          selectedMarker={selectedMarker}
          onSelectMarker={handleSelectActiveMarker}
          onClearSelection={handleClearMarkerSelection}
          historicalLookup={historicalLookup}
          journeyTrail={journeyTrail}
          filterKey={`${selectedZone}|${selectedPs}|${selectedHeightBucket}|${searchTerm}`}
        />
      </div>

      {viewMode === 'split' && (
        <div className="h-2/5 w-full">
          <IdolTable
            searchTerm={searchTerm}
            selectedZone={selectedZone}
            selectedPs={selectedPs}
            selectedStateFilter={selectedStateFilter}
            selectedHeightBucket={selectedHeightBucket}
            isImmersionsToday={isImmersionsToday}
            selectedGpid={selectedMarker?.gpid || null}
            onSelectIdol={handleSelectIdol}
          />
        </div>
      )}
    </div>
  );
};
