import React, { Suspense, lazy } from 'react';
import { Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { TrackingProvider } from './context/TrackingContext';
import { canManageAssignments, isMainOfficer } from './context/AuthContext';
import { RequireAuth, RequireRole } from './routes/guards';
import { AppLayout } from './components/layout/AppLayout';
import { LoadingState } from './components/shared/States';

const LoginPage = lazy(() => import('./pages/LoginPage').then((m) => ({ default: m.LoginPage })));
const DashboardPage = lazy(() => import('./pages/DashboardPage').then((m) => ({ default: m.DashboardPage })));
const LiveMapPage = lazy(() => import('./pages/LiveMapPage').then((m) => ({ default: m.LiveMapPage })));
const ProcessionsPage = lazy(() => import('./pages/ProcessionsPage').then((m) => ({ default: m.ProcessionsPage })));
const PoliceStationsPage = lazy(() => import('./pages/PoliceStationsPage').then((m) => ({ default: m.PoliceStationsPage })));
const AlertsPage = lazy(() => import('./pages/AlertsPage').then((m) => ({ default: m.AlertsPage })));
const ReportsPage = lazy(() => import('./pages/ReportsPage').then((m) => ({ default: m.ReportsPage })));
const HoldingPointsPage = lazy(() => import('./pages/HoldingPointsPage').then((m) => ({ default: m.HoldingPointsPage })));
const VisarjanPointsPage = lazy(() => import('./pages/VisarjanPointsPage').then((m) => ({ default: m.VisarjanPointsPage })));
const AssignmentsPage = lazy(() => import('./pages/AssignmentsPage').then((m) => ({ default: m.AssignmentsPage })));
const UsersPage = lazy(() => import('./pages/UsersPage').then((m) => ({ default: m.UsersPage })));
const RolesPage = lazy(() => import('./pages/RolesPage').then((m) => ({ default: m.RolesPage })));
const SettingsPage = lazy(() => import('./pages/SettingsPage').then((m) => ({ default: m.SettingsPage })));
const AccessDeniedPage = lazy(() => import('./pages/AccessDeniedPage').then((m) => ({ default: m.AccessDeniedPage })));
const NotFoundPage = lazy(() => import('./pages/NotFoundPage').then((m) => ({ default: m.NotFoundPage })));

const PageFallback: React.FC = () => (
  <div className="h-full flex items-center justify-center">
    <LoadingState label="Loading…" />
  </div>
);

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <Suspense fallback={<PageFallback />}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />

          <Route element={<RequireAuth />}>
            <Route
              element={
                <TrackingProvider>
                  <AppLayout />
                </TrackingProvider>
              }
            >
              <Route index element={<DashboardPage />} />
              <Route path="live-map" element={<LiveMapPage />} />
              <Route path="processions" element={<ProcessionsPage />} />
              <Route path="police-stations" element={<PoliceStationsPage />} />
              <Route path="alerts" element={<AlertsPage />} />
              <Route path="reports" element={<ReportsPage />} />
              <Route path="holding-points" element={<HoldingPointsPage />} />
              <Route path="visarjan-points" element={<VisarjanPointsPage />} />

              <Route element={<RequireRole allow={canManageAssignments} />}>
                <Route path="assignments" element={<AssignmentsPage />} />
              </Route>

              <Route element={<RequireRole allow={isMainOfficer} />}>
                <Route path="users" element={<UsersPage />} />
                <Route path="roles" element={<RolesPage />} />
              </Route>

              <Route path="settings" element={<SettingsPage />} />
              <Route path="access-denied" element={<AccessDeniedPage />} />
            </Route>
          </Route>

          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </Suspense>
    </AuthProvider>
  );
};
