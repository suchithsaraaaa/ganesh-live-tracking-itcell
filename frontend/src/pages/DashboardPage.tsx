import React from 'react';
import { useTracking } from '../context/TrackingContext';
import { KpiCards } from '../components/KpiCards';
import { LiveMap } from '../components/LiveMap';
import { ZoneStatusPanel } from '../components/dashboard/ZoneStatusPanel';
import { RecentAlertsPanel } from '../components/dashboard/RecentAlertsPanel';
import { ActiveProcessionsTable } from '../components/dashboard/ActiveProcessionsTable';

export const DashboardPage: React.FC = () => {
  const {
    kpis, selectedStateFilter, setSelectedStateFilter,
    filteredMarkers, selectedMarker, handleSelectMarker, handleClearSelection,
    historicalLookup, journeyTrail,
    selectedZone, setSelectedZone,
  } = useTracking();

  return (
    <div className="h-full flex flex-col overflow-y-auto animate-fade-in-up">
      <KpiCards
        kpis={kpis}
        selectedStateFilter={selectedStateFilter}
        onSelectStateFilter={setSelectedStateFilter}
      />

      <div className="flex-1 flex flex-col gap-4 p-4 lg:p-6 min-h-[560px]">
        <div className="flex-1 flex flex-col xl:flex-row gap-4 min-h-[380px]">
          <div className="flex-1 min-h-[320px] rounded-lg overflow-hidden border border-border-subtle relative">
            <LiveMap
              markers={filteredMarkers}
              selectedMarker={selectedMarker}
              onSelectMarker={handleSelectMarker}
              onClearSelection={handleClearSelection}
              historicalLookup={historicalLookup}
              journeyTrail={journeyTrail}
            />
          </div>

          <div className="w-full xl:w-80 shrink-0 flex flex-col gap-4">
            <ZoneStatusPanel
              markers={filteredMarkers}
              selectedZone={selectedZone}
              onSelectZone={setSelectedZone}
            />
            <RecentAlertsPanel markers={filteredMarkers} onSelectAlert={handleSelectMarker} />
          </div>
        </div>

        <div>
          <h2 className="text-[11px] font-semibold tracking-wider uppercase text-text-primary mb-2 px-1">
            Active Processions
          </h2>
          <ActiveProcessionsTable
            markers={filteredMarkers}
            selectedGpid={selectedMarker?.gpid || null}
            onSelectMarker={handleSelectMarker}
          />
        </div>
      </div>
    </div>
  );
};
