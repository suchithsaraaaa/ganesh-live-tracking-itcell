import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { RefreshCw, UserCheck, LogOut } from 'lucide-react';
import { useAuth, formatUserIdentity } from '../context/AuthContext';
import { useTracking } from '../context/TrackingContext';
import telanganaPoliceLogo from '../assets/branding/telangana-police-logo.png';

export const Header: React.FC = () => {
  const { user, logout } = useAuth();
  const { lastUpdated, isRefreshing, loadDashboard } = useTracking();
  const navigate = useNavigate();
  const [loggingOut, setLoggingOut] = useState(false);

  const now = new Date();
  const dateLabel = now.toLocaleDateString(undefined, {
    weekday: 'short',
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });

  const handleLogout = async () => {
    setLoggingOut(true);
    try {
      await logout();
      navigate('/login', { replace: true });
    } finally {
      setLoggingOut(false);
    }
  };

  return (
    <header className="glass h-16 border-b flex items-center justify-between px-6 z-20 shrink-0">
      <div className="flex items-center gap-3">
        <img
          src={telanganaPoliceLogo}
          alt="Telangana State Police"
          className="h-8 w-auto object-contain shrink-0"
        />
        <div className="leading-tight">
          <h1 className="text-sm font-semibold text-text-primary">Hyderabad City Police</h1>
          <p className="text-xs text-text-secondary">Ganesh Visarjan Monitoring System</p>
        </div>
      </div>

      <div className="hidden md:flex flex-col items-center leading-tight select-none">
        <span className="text-[11px] font-semibold tracking-[0.12em] text-accent uppercase">
          Ganesh Chaturthi
        </span>
        <span className="text-[10px] text-text-tertiary">A Safer, United Hyderabad</span>
      </div>

      <div className="flex items-center gap-5">
        <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded bg-status-active-soft">
          <span className="w-1.5 h-1.5 rounded-full bg-status-active live-pulse" />
          <span className="text-[10px] font-medium tracking-wider uppercase text-status-active">
            {isRefreshing ? 'Syncing' : 'Live'}
          </span>
        </div>

        <span className="text-xs mono text-text-tertiary hidden lg:inline">
          {dateLabel} &nbsp; {lastUpdated ? lastUpdated.toLocaleTimeString() : '--:--:--'}
        </span>

        <button
          onClick={() => loadDashboard(true)}
          title="Refresh now"
          className="text-text-tertiary hover:text-accent transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-accent' : ''}`} />
        </button>

        <div className="w-px h-6 bg-border-subtle" />

        <div className="flex items-center gap-2.5">
          <div className="w-[26px] h-[26px] rounded-full bg-elevated-2 border border-border-default flex items-center justify-center shrink-0">
            <UserCheck className="w-3.5 h-3.5 text-status-active" />
          </div>
          <div className="text-right leading-tight hidden sm:block">
            <div className="text-xs font-medium text-text-primary">
              {user?.username || 'Unknown User'}
            </div>
            <div className="text-[10px] text-text-tertiary">
              {user ? formatUserIdentity(user).fullLabel : ''}
            </div>
          </div>
        </div>

        <button
          onClick={handleLogout}
          disabled={loggingOut}
          title="Log out"
          className="text-text-tertiary hover:text-status-critical transition-colors disabled:opacity-50"
        >
          <LogOut className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};
