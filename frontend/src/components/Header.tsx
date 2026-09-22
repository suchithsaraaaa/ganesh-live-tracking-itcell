import React from 'react';
import { Shield, RefreshCw, UserCheck } from 'lucide-react';
import { User } from '../types';

interface HeaderProps {
  user: User | null;
  lastUpdated: Date | null;
  isRefreshing: boolean;
  onRefresh: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  user,
  lastUpdated,
  isRefreshing,
  onRefresh,
}) => {
  return (
    <header className="h-14 bg-slate-950 border-b border-slate-800 flex items-center justify-between px-4 z-20 shrink-0">
      <div className="flex items-center space-x-3">
        <div className="p-1.5 bg-blue-900/60 rounded-md border border-blue-500/30 flex items-center justify-center">
          <Shield className="w-5 h-5 text-blue-400" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-sm font-bold tracking-wide text-white uppercase">
              Hyderabad Police &bull; Ganesh Visarjan Live Tracking
            </h1>
            <span className="px-2 py-0.5 text-[10px] font-semibold tracking-wider uppercase bg-blue-950 text-blue-400 border border-blue-800 rounded">
              Command Center
            </span>
          </div>
          <p className="text-[11px] text-slate-400">
            Telangana Police &bull; Operation Visarjan 2026 Bandobust Monitoring
          </p>
        </div>
      </div>

      <div className="flex items-center space-x-4">
        {/* Polling Pulse */}
        <div className="flex items-center space-x-2 text-xs text-slate-400 bg-slate-900 px-2.5 py-1 rounded border border-slate-800">
          <span className="w-2 h-2 rounded-full bg-emerald-500 live-pulse"></span>
          <span>Live Sync {lastUpdated ? `(${lastUpdated.toLocaleTimeString()})` : '(10s)'}</span>
          <button
            onClick={onRefresh}
            title="Refresh now"
            className="hover:text-blue-400 transition-colors ml-1"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-blue-400' : ''}`} />
          </button>
        </div>

        {/* User / Officer Info */}
        <div className="flex items-center space-x-2 text-xs border-l border-slate-800 pl-4">
          <UserCheck className="w-4 h-4 text-emerald-400" />
          <div className="text-right">
            <div className="font-semibold text-slate-200">
              {user?.username || 'Main Control Room'}
            </div>
            <div className="text-[10px] text-slate-400">
              {user?.role ? user.role.replace('_', ' ') : 'System Officer'} &bull; {user?.police_station || 'City Wide'}
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
