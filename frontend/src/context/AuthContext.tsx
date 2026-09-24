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

export function isSuperAdmin(user: User | null): boolean {
  return user?.role === 'SUPER_ADMIN';
}

export function isMainOfficer(user: User | null): boolean {
  return user?.role === 'SUPER_ADMIN' || user?.role === 'MAIN_OFFICER' || user?.role === 'SYS_ADMIN';
}

export function isSysAdmin(user: User | null): boolean {
  return user?.role === 'SYS_ADMIN';
}

/** Mirrors backend IsStationOfficerOrAbove: who can create/manage assignments. */
export function canManageAssignments(user: User | null): boolean {
  const roles: UserRole[] = ['SUPER_ADMIN', 'MAIN_OFFICER', 'SYS_ADMIN', 'ACP', 'SHO'];
  return !!user && (roles.includes(user.role) || (user.permissions || []).includes('assign_field_officers'));
}

export function roleLabel(role: UserRole, user?: { zone?: string | null } | null): string {
  if (role === 'SYS_ADMIN') {
    if (user && !user.zone) return 'System Admin (Unassigned Zone)';
    return 'Zonal System Admin';
  }
  switch (role) {
    case 'SUPER_ADMIN': return 'Super Administrator';
    case 'MAIN_OFFICER': return 'Main Officer';
    case 'ACP': return 'ACP / Senior Officer';
    case 'SHO': return 'Station House Officer';
    case 'CONSTABLE': return 'Constable / Ground Staff';
    default: return role;
  }
}

export function formatUserIdentity(user: User | null): { roleText: string; scopeText: string; fullLabel: string } {
  if (!user) return { roleText: '', scopeText: '', fullLabel: '' };
  if (user.role === 'SUPER_ADMIN') {
    return { roleText: 'Super Administrator', scopeText: 'City Wide', fullLabel: 'Super Administrator • City Wide' };
  }
  if (user.role === 'MAIN_OFFICER') {
    const scope = user.zone ? user.zone : 'City Wide';
    return { roleText: 'Main Officer', scopeText: scope, fullLabel: `Main Officer • ${scope}` };
  }
  if (user.role === 'SYS_ADMIN') {
    const scope = user.zone ? user.zone : 'Unassigned Zone';
    const rText = user.zone ? 'Zonal System Admin' : 'System Admin (Unassigned Zone)';
    return { roleText: rText, scopeText: scope, fullLabel: `${rText} • ${scope}` };
  }
  const rText = roleLabel(user.role, user);
  const scope = user.police_station || user.zone || 'Unassigned';
  return { roleText: rText, scopeText: scope, fullLabel: `${rText} • ${scope}` };
}

