import React, { useState } from 'react';
import { useTracking } from '../context/TrackingContext';
import { ActiveProcessionsTable } from '../components/dashboard/ActiveProcessionsTable';
import { IdolTable } from '../components/IdolTable';

type Tab = 'active' | 'holding' | 'visarjan' | 'immersed';

const TABS: { key: Tab; label: string }[] = [
  { key: 'active', label: 'Active Tracking' },
  { key: 'holding', label: 'Holding' },
  { key: 'visarjan', label: 'At Visarjan' },
  { key: 'immersed', label: 'Immersed' },
];

export const ProcessionsPage: React.FC = () => {
  const { activeMarkers, selectedMarker, handleSelectMarker, handleSelectIdol } = useTracking();
  const [tab, setTab] = useState<Tab>('active');

  const holdingMarkers = activeMarkers.filter((m) => m.procession_state === 'HOLDING');

  return (
    <div className="h-full flex flex-col overflow-hidden animate-fade-in-up">
      <div className="px-6 pt-6 pb-3">
        <h1 className="text-lg font-semibold text-text-primary">Processions</h1>
        <p className="text-xs text-text-tertiary mt-0.5">
          Live and registry-wide view of every Ganesh procession by operational state.
        </p>
      </div>

      <div className="flex items-center gap-1 px-6 border-b border-border-subtle">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-3 py-2.5 text-[12px] font-medium border-b-2 -mb-px transition-colors ${
              tab === t.key ? 'text-text-primary border-accent' : 'text-text-tertiary border-transparent hover:text-text-secondary'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {tab === 'active' && (
          <ActiveProcessionsTable
            markers={activeMarkers}
            selectedGpid={selectedMarker?.gpid || null}
            onSelectMarker={handleSelectMarker}
          />
        )}
        {tab === 'holding' && (
          <ActiveProcessionsTable
            markers={holdingMarkers}
            selectedGpid={selectedMarker?.gpid || null}
            onSelectMarker={handleSelectMarker}
          />
        )}
        {tab === 'visarjan' && (
          <div className="h-[calc(100vh-220px)] -mx-6">
            <IdolTable
              searchTerm=""
              selectedZone="All Zones"
              selectedPs=""
              selectedStateFilter="AT_VISARJAN"
              selectedGpid={selectedMarker?.gpid || null}
              onSelectIdol={handleSelectIdol}
            />
          </div>
        )}
        {tab === 'immersed' && (
          <div className="h-[calc(100vh-220px)] -mx-6">
            <IdolTable
              searchTerm=""
              selectedZone="All Zones"
              selectedPs=""
              selectedStateFilter="IMMERSION_COMPLETED"
              selectedGpid={selectedMarker?.gpid || null}
              onSelectIdol={handleSelectIdol}
            />
          </div>
        )}
      </div>
    </div>
  );
};
