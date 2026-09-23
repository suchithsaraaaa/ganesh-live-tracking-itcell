import React from 'react';
import { useTracking } from '../context/TrackingContext';
import { KpiCards } from '../components/KpiCards';
import { LiveMap } from '../components/LiveMap';
import { ZoneStatusPanel } from '../components/dashboard/ZoneStatusPanel';
import { RecentAlertsPanel } from '../components/dashboard/RecentAlertsPanel';
import { ActiveProcessionsTable } from '../components/dashboard/ActiveProcessionsTable';

import { Calendar, Filter } from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const {
    kpis, selectedStateFilter, setSelectedStateFilter,
    selectedHeightBucket, setSelectedHeightBucket,
    isImmersionsToday, setIsImmersionsToday,
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
        isImmersionsToday={isImmersionsToday}
        onToggleImmersionsToday={() => setIsImmersionsToday(!isImmersionsToday)}
      />

      <div className="flex-1 flex flex-col gap-4 p-4 lg:p-6 min-h-[560px]">
        {/* Operational Quick Filter Strip */}
        <div className="flex flex-wrap items-center justify-between gap-3 px-3 py-2 bg-elevated-1 border border-border-subtle rounded-lg text-xs">
          <div className="flex items-center space-x-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-text-tertiary flex items-center gap-1.5">
              <Filter className="w-3 h-3 text-accent" />
              Height Filter (&ge;15ft):
            </span>
            <div className="flex items-center space-x-1">
              {[
                { id: 'ALL', label: 'All 15+ ft' },
                { id: '15_20', label: '15–20 ft (Green)', dot: '#10B981' },
                { id: '21_25', label: '21–25 ft (Yellow)', dot: '#F59E0B' },
                { id: 'above_25', label: '26+ ft (Red)', dot: '#EF4444' },
              ].map((btn) => (
                <button
                  key={btn.id}
                  onClick={() => setSelectedHeightBucket(btn.id)}
                  className={`px-2.5 py-1 rounded text-[11px] font-medium transition-colors flex items-center space-x-1.5 border ${
                    selectedHeightBucket === btn.id
                      ? 'bg-accent/15 text-accent border-accent/40 font-semibold'
                      : 'bg-elevated-2 text-text-secondary border-border-default hover:text-text-primary hover:border-border-subtle'
                  }`}
                >
                  {btn.dot && (
                    <span
                      className="w-2 h-2 rounded-full shrink-0"
                      style={{ backgroundColor: btn.dot }}
                    />
                  )}
                  <span>{btn.label}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => setIsImmersionsToday(!isImmersionsToday)}
              className={`px-3 py-1 rounded text-[11px] font-medium transition-all flex items-center space-x-1.5 border ${
                isImmersionsToday
                  ? 'bg-amber-500/20 text-amber-300 border-amber-500/50 shadow-sm shadow-amber-500/10'
                  : 'bg-elevated-2 text-text-secondary border-border-default hover:text-text-primary hover:border-border-subtle'
              }`}
            >
              <Calendar className="w-3 h-3" />
              <span>Immersions Today</span>
              {isImmersionsToday && (
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse ml-0.5" />
              )}
            </button>
          </div>
        </div>

        <div className="flex-1 flex flex-col xl:flex-row gap-4 min-h-[380px]">
          <div className="flex-1 min-h-[320px] rounded-lg overflow-hidden border border-border-subtle relative">
            <LiveMap
              markers={filteredMarkers}
              selectedMarker={selectedMarker}
              onSelectMarker={handleSelectMarker}
              onClearSelection={handleClearSelection}
              historicalLookup={historicalLookup}
              journeyTrail={journeyTrail}
              filterKey={`${selectedZone}|${selectedHeightBucket}|${isImmersionsToday}|${selectedStateFilter}`}
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
