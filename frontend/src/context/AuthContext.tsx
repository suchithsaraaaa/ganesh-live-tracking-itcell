import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { User, UserRole } from '../types';
import { fetchCurrentUser, login as apiLogin, logout as apiLogout } from '../api/client';

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    fetchCurrentUser()
      .then(setUser)
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const loggedInUser = await apiLogin(username, password);
    setUser(loggedInUser);
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiLogout();
    } finally {
      setUser(null);
    }
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
}

// ---------------------------------------------------------------------------
// Role helpers
//
// These mirror the backend's real role hierarchy (common/permissions.py) and
// are UI-visibility hints only — the backend remains the authorization
// boundary on every request regardless of what the frontend shows or hides.
// ---------------------------------------------------------------------------

export function isMainOfficer(user: User | null): boolean {
  return user?.role === 'MAIN_OFFICER';
}

/** Mirrors backend IsStationOfficerOrAbove: who can create/manage assignments. */
export function canManageAssignments(user: User | null): boolean {
  const roles: UserRole[] = ['MAIN_OFFICER', 'ACP', 'SHO'];
  return !!user && roles.includes(user.role);
}

export function roleLabel(role: UserRole): string {
  switch (role) {
    case 'MAIN_OFFICER': return 'Main Officer / System Admin';
    case 'ACP': return 'ACP / Senior Officer';
    case 'SHO': return 'Station House Officer';
    case 'CONSTABLE': return 'Constable / Ground Staff';
    default: return role;
  }
}
