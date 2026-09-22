import React, { useState } from 'react';
import { Map, Table } from 'lucide-react';
import { useTracking } from '../context/TrackingContext';
import { SearchFilterBar } from '../components/SearchFilterBar';
import { LiveMap } from '../components/LiveMap';
import { IdolTable } from '../components/IdolTable';

export const LiveMapPage: React.FC = () => {
  const {
    searchTerm, setSearchTerm, selectedZone, setSelectedZone, selectedPs, setSelectedPs,
    clearFilters, filteredMarkers, selectedMarker, handleSelectMarker, handleClearSelection,
    historicalLookup, journeyTrail, selectedStateFilter, handleSelectIdol,
  } = useTracking();

  const [viewMode, setViewMode] = useState<'map' | 'split'>('map');

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
            onClear={clearFilters}
          />
        </div>

        <div className="flex items-center space-x-1 bg-elevated-2 p-1 rounded-md border border-border-default text-xs shrink-0 ml-2">
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

      {viewMode === 'split' && (
        <div className="h-2/5 w-full">
          <IdolTable
            searchTerm={searchTerm}
            selectedZone={selectedZone}
            selectedPs={selectedPs}
            selectedStateFilter={selectedStateFilter}
            selectedGpid={selectedMarker?.gpid || null}
            onSelectIdol={handleSelectIdol}
          />
        </div>
      )}
    </div>
  );
};
