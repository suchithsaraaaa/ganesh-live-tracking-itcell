import React from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { User } from '../types';

/** Blocks unauthenticated visitors from every protected route, redirecting to /login. */
export const RequireAuth: React.FC = () => {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-base text-text-tertiary text-sm">
        Verifying session…
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <Outlet />;
};

/**
 * Gates a route to a UI-visibility predicate over the current user. This is a
 * convenience for the nav/UX only — every underlying API call remains
 * authoritatively enforced server-side regardless of what this shows.
 */
export const RequireRole: React.FC<{ allow: (user: User | null) => boolean }> = ({ allow }) => {
  const { user } = useAuth();
  if (!allow(user)) return <Navigate to="/access-denied" replace />;
  return <Outlet />;
};
