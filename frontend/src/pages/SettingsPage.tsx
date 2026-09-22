import React from 'react';
import { useNavigate } from 'react-router-dom';
import { LogOut, ShieldCheck } from 'lucide-react';
import { useAuth, roleLabel } from '../context/AuthContext';

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <span className="text-[10px] uppercase tracking-wide text-text-tertiary">{label}</span>
      <p className="text-sm text-text-primary mt-0.5">{value || '—'}</p>
    </div>
  );
}

export const SettingsPage: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  return (
    <div className="h-full overflow-y-auto animate-fade-in-up">
      <div className="px-6 pt-6 pb-4">
        <h1 className="text-lg font-semibold text-text-primary">Settings</h1>
        <p className="text-xs text-text-tertiary mt-0.5">Profile and system information for your session.</p>
      </div>

      <div className="px-6 pb-6 max-w-2xl space-y-4">
        <section className="bg-elevated border border-border-subtle rounded-lg p-5">
          <div className="flex items-center gap-2 mb-4">
            <ShieldCheck className="w-4 h-4 text-accent" strokeWidth={1.8} />
            <h2 className="text-[11px] font-semibold uppercase tracking-wider text-text-primary">Profile</h2>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Username" value={user?.username} />
            <Field label="Role" value={user ? roleLabel(user.role) : ''} />
            <Field label="Police ID" value={user?.police_id} />
            <Field label="Zone" value={user?.zone} />
            <Field label="Division" value={user?.division} />
            <Field label="Police Station" value={user?.police_station || 'City Wide'} />
          </div>
          <p className="text-[11px] text-text-tertiary mt-4 pt-4 border-t border-border-subtle">
            Password changes and profile edits are managed by your system administrator — this
            application does not currently expose a self-service password-change API.
          </p>
        </section>

        <section className="bg-elevated border border-border-subtle rounded-lg p-5">
          <h2 className="text-[11px] font-semibold uppercase tracking-wider text-text-primary mb-3">System</h2>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Application" value="Ganesh Visarjan Monitoring System" />
            <Field label="Version" value="1.0.0" />
          </div>
        </section>

        <button
          onClick={handleLogout}
          className="flex items-center gap-2 px-4 py-2.5 rounded-md bg-status-critical-soft text-status-critical text-sm font-medium hover:opacity-80 transition-opacity"
        >
          <LogOut className="w-4 h-4" />
          Log out
        </button>
      </div>
    </div>
  );
};
