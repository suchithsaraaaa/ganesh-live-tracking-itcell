import React from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from '../Header';
import { IdolDetailDrawer } from '../IdolDetailDrawer';
import { TimestampLookupModal } from '../TimestampLookupModal';
import { AssignmentModal } from '../AssignmentModal';
import { useTracking } from '../../context/TrackingContext';

export const AppLayout: React.FC = () => {
  const {
    selectedMarker, isDrawerOpen, handleClearSelection,
    openTimestampLookup, openAssignment, handleToggleJourney,
    journeyTrail, isLoadingJourney,
    timestampModalOpen, targetGpidForLookup, closeTimestampLookup, setHistoricalLookup,
    assignmentModalOpen, targetGpidForAssignment, closeAssignment, loadDashboard,
  } = useTracking();

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-base text-text-primary">
      <Sidebar />

      <div className="flex-1 flex flex-col h-full overflow-hidden relative">
        <Header />
        <main className="flex-1 overflow-hidden relative">
          <Outlet />
        </main>
      </div>

      {isDrawerOpen && selectedMarker && (
        <div className="fixed right-0 top-16 bottom-0 z-30 animate-slide-in-right">
          <IdolDetailDrawer
            marker={selectedMarker}
            isOpen={isDrawerOpen}
            onClose={handleClearSelection}
            onOpenTimestampLookup={openTimestampLookup}
            onOpenAssignment={openAssignment}
            onToggleJourney={handleToggleJourney}
            isJourneyActive={Boolean(journeyTrail)}
            isLoadingJourney={isLoadingJourney}
            journeyTrail={journeyTrail}
          />
        </div>
      )}

      <TimestampLookupModal
        isOpen={timestampModalOpen}
        initialGpid={targetGpidForLookup}
        onClose={closeTimestampLookup}
        onPlotPoint={(result) => setHistoricalLookup(result)}
      />

      <AssignmentModal
        isOpen={assignmentModalOpen}
        gpid={targetGpidForAssignment}
        currentAssignmentId={null}
        currentConstableName={selectedMarker?.assigned_constable?.name}
        onClose={closeAssignment}
        onSuccess={() => loadDashboard(true)}
      />
    </div>
  );
};
