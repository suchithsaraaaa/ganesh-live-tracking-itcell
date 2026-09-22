import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Map,
  Footprints,
  Building2,
  FileText,
  Bell,
  PauseCircle,
  Waves,
  Users,
  KeyRound,
  ClipboardList,
  Settings,
  Shield,
  LucideIcon,
} from 'lucide-react';
import { useAuth, canManageAssignments, isMainOfficer } from '../../context/AuthContext';
import { GaneshaMark } from '../shared/GaneshaMark';

interface NavEntry {
  key: string;
  label: string;
  icon: LucideIcon;
  to?: string;
  enabled: boolean;
}

export const Sidebar: React.FC = () => {
  const { user } = useAuth();

  const primaryNav: NavEntry[] = [
    { key: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, to: '/', enabled: true },
    { key: 'liveMap', label: 'Live Map', icon: Map, to: '/live-map', enabled: true },
    { key: 'processions', label: 'Processions', icon: Footprints, to: '/processions', enabled: true },
    { key: 'policeStations', label: 'Police Stations', icon: Building2, to: '/police-stations', enabled: true },
    { key: 'reports', label: 'Reports', icon: FileText, to: '/reports', enabled: true },
    { key: 'alerts', label: 'Alerts', icon: Bell, to: '/alerts', enabled: true },
    { key: 'holdingPoints', label: 'Holding Points', icon: PauseCircle, to: '/holding-points', enabled: true },
    { key: 'visarjanPoints', label: 'Visarjan Points', icon: Waves, to: '/visarjan-points', enabled: true },
  ];

  const adminNav: NavEntry[] = [
    {
      key: 'assignments',
      label: 'Officer Assignment',
      icon: ClipboardList,
      to: '/assignments',
      enabled: canManageAssignments(user),
    },
    { key: 'users', label: 'Users', icon: Users, to: '/users', enabled: isMainOfficer(user) },
    { key: 'roles', label: 'Roles & Permissions', icon: KeyRound, enabled: false },
    { key: 'settings', label: 'Settings', icon: Settings, to: '/settings', enabled: true },
  ];

  // Admin section only shown to roles who can act on at least one item in it
  const showAdminSection = canManageAssignments(user) || isMainOfficer(user);

  const renderEntry = (item: NavEntry) => {
    const Icon = item.icon;
    if (!item.enabled || !item.to) {
      return (
        <div
          key={item.key}
          title={`${item.label} — coming soon`}
          className="w-full flex items-center justify-center lg:justify-start gap-2.5 px-2.5 lg:pl-2.5 lg:pr-3 py-2.5 rounded-md text-[13px] border-l-2 border-l-transparent text-text-tertiary/60 cursor-not-allowed"
        >
          <Icon className="w-4 h-4 shrink-0" strokeWidth={1.8} />
          <span className="truncate hidden lg:inline">{item.label}</span>
        </div>
      );
    }
    return (
      <NavLink
        key={item.key}
        to={item.to}
        end={item.to === '/'}
        className={({ isActive }) =>
          `group w-full flex items-center justify-center lg:justify-start gap-2.5 px-2.5 lg:pl-2.5 lg:pr-3 py-2.5 rounded-md text-[13px] transition-colors duration-150 border-l-2 ${
            isActive
              ? 'bg-elevated border-l-accent text-text-primary font-medium'
              : 'border-l-transparent text-text-secondary hover:text-text-primary hover:bg-elevated/60'
          }`
        }
      >
        {({ isActive }) => (
          <>
            <Icon className={`w-4 h-4 shrink-0 transition-colors ${isActive ? 'text-accent' : ''}`} strokeWidth={1.8} />
            <span className="truncate hidden lg:inline">{item.label}</span>
          </>
        )}
      </NavLink>
    );
  };

  return (
    <aside className="glass w-16 lg:w-60 h-full shrink-0 flex flex-col border-r transition-[width]">
      {/* Brand */}
      <div className="px-3 lg:px-6 pt-6 pb-5 flex justify-center lg:justify-start">
        <div className="flex items-center gap-2.5">
          <Shield className="w-[22px] h-[22px] text-accent shrink-0" strokeWidth={1.6} />
          <div className="leading-tight hidden lg:block">
            <div className="text-[15px] font-semibold text-text-primary tracking-tight">HYDERABAD</div>
            <div className="text-[15px] font-semibold text-text-primary tracking-tight">CITY POLICE</div>
          </div>
        </div>
      </div>

      <div className="h-px bg-border-subtle" />

      {/* Navigation */}
      <nav className="flex-1 px-2 lg:px-3 pt-3 space-y-0.5 overflow-y-auto overflow-x-hidden">
        {primaryNav.map(renderEntry)}

        {showAdminSection && (
          <>
            <div className="pt-3 pb-1 px-2.5 hidden lg:block">
              <span className="text-[10px] font-medium tracking-wider uppercase text-text-tertiary">Administration</span>
            </div>
            <div className="lg:hidden h-px bg-border-subtle my-2" />
            {adminNav.map(renderEntry)}
          </>
        )}
        {!showAdminSection && renderEntry(adminNav[adminNav.length - 1])}
      </nav>

      <div className="h-px bg-border-subtle" />

      {/* Ganesh Chaturthi identity signature */}
      <div className="px-3 lg:px-6 py-5 flex flex-col items-center gap-2">
        <GaneshaMark className="w-9 h-9 lg:w-11 lg:h-11 text-accent/80" />
        <p className="hidden lg:block text-[11px] text-text-tertiary text-center tracking-wide">
          || Ganpati Bappa Morya ||
        </p>
      </div>
    </aside>
  );
};
