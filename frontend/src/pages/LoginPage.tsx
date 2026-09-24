import React, { useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { Eye, EyeOff, Lock, User as UserIcon } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { GaneshaMark } from '../components/shared/GaneshaMark';
import { ApiError } from '../api/client';
import telanganaPoliceLogo from '../assets/branding/telangana-police-logo.png';

export const LoginPage: React.FC = () => {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (user) {
    const from = (location.state as { from?: Location })?.from?.pathname || '/';
    return <Navigate to={from} replace />;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(username.trim(), password);
      const from = (location.state as { from?: Location })?.from?.pathname || '/';
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to reach the authentication service.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="h-screen w-screen flex bg-base overflow-hidden">
      {/* LEFT — cinematic hero */}
      <div className="hidden md:flex md:w-1/2 lg:w-3/5 relative flex-col justify-between overflow-hidden">
        {/* Layered dark gradient wash, standing in for a photographic hero since no
            image-generation tool is available in this session — see build notes. */}
        <div
          className="absolute inset-0"
          style={{
            background:
              'radial-gradient(120% 90% at 15% 20%, rgba(217,121,59,0.16), transparent 55%), ' +
              'radial-gradient(90% 70% at 85% 85%, rgba(94,136,168,0.10), transparent 60%), ' +
              'linear-gradient(160deg, #0d0e0c 0%, #0b0b0a 55%, #090a09 100%)',
          }}
        />

        {/* Subtle temple skyline silhouette */}
        <svg
          className="absolute bottom-0 left-0 w-full h-1/2 opacity-[0.08]"
          viewBox="0 0 800 300"
          preserveAspectRatio="xMidYMax slice"
          fill="currentColor"
          style={{ color: '#F2EFE9' }}
        >
          <path d="M0 300V220h40l10-30 10 30h30V190l20-40 20 40v30h40V170l15-35 15 35v50h50V150l25-55 25 55v70h50V180l15-30 15 30v40h40V210l10-25 10 25h30V240h60V190l20-40 20 40v50h40V220h30l10-25 10 25h20V300Z" />
        </svg>

        <div className="relative z-10 p-10 lg:p-14 flex items-center gap-4">
          <img
            src={telanganaPoliceLogo}
            alt="Telangana State Police"
            className="h-24 lg:h-28 w-auto object-contain shrink-0 drop-shadow-xl"
          />
          <div className="leading-tight">
            <div className="text-[11px] font-bold text-accent uppercase tracking-widest mb-1">
              Telangana State Police
            </div>
            <div className="text-xl lg:text-2xl font-bold text-text-primary tracking-tight">
              HYDERABAD CITY POLICE
            </div>
            <div className="text-xs text-text-tertiary mt-0.5">
              Ganesh Visarjan Monitoring System
            </div>
          </div>
        </div>

        <div className="relative z-10 px-10 lg:px-14 pb-16 flex flex-col items-start gap-6">
          <GaneshaMark className="w-24 h-24 text-accent/70" />
          <div>
            <h1 className="text-3xl lg:text-4xl font-semibold text-text-primary tracking-tight leading-tight">
              A Safer,<br />United Hyderabad
            </h1>
            <p className="mt-3 text-sm text-text-tertiary max-w-sm">
              Live operational command center for Ganesh Chaturthi procession &amp; immersion monitoring
              across the Hyderabad City Police commissionerate.
            </p>
          </div>
        </div>
      </div>

      {/* RIGHT — login panel */}
      <div className="flex-1 flex items-center justify-center px-6">
        <div className="w-full max-w-sm animate-fade-in-up">
          <div className="md:hidden flex flex-col items-center gap-2 mb-6">
            <img
              src={telanganaPoliceLogo}
              alt="Telangana State Police"
              className="h-16 w-auto object-contain drop-shadow"
            />
            <div className="text-center leading-tight">
              <div className="text-[10px] font-bold text-accent uppercase tracking-wider">
                Telangana State Police
              </div>
              <div className="text-base font-bold text-text-primary">HYDERABAD CITY POLICE</div>
              <div className="text-xs text-text-tertiary">Ganesh Visarjan Monitoring System</div>
            </div>
          </div>

          <div className="glass border rounded-xl p-8 shadow-2xl">
            <h2 className="text-lg font-semibold text-text-primary">Authorized Personnel Only</h2>
            <p className="text-xs text-text-tertiary mt-1 mb-6">
              Sign in with your department-issued credentials.
            </p>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-[11px] font-medium text-text-secondary mb-1.5">
                  Username / Email
                </label>
                <div className="relative">
                  <UserIcon className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-text-tertiary" />
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="Enter your credentials"
                    autoComplete="username"
                    required
                    autoFocus
                    className="w-full pl-9 pr-3 py-2.5 bg-elevated-2 border border-border-default rounded-md text-text-primary text-sm focus:outline-none focus:border-accent transition-colors"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-medium text-text-secondary mb-1.5">
                  Password
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-text-tertiary" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter your password"
                    autoComplete="current-password"
                    required
                    className="w-full pl-9 pr-9 py-2.5 bg-elevated-2 border border-border-default rounded-md text-text-primary text-sm focus:outline-none focus:border-accent transition-colors"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((s) => !s)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-text-tertiary hover:text-text-secondary transition-colors"
                    tabIndex={-1}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {error && (
                <div className="text-xs text-status-critical bg-status-critical-soft border border-status-critical/30 rounded-md px-3 py-2">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={submitting}
                className="w-full py-2.5 bg-accent hover:bg-accent-hover disabled:opacity-60 text-base font-medium rounded-md transition-colors flex items-center justify-center gap-2"
              >
                {submitting ? 'Signing in…' : 'Login'}
              </button>

              <p className="text-[11px] text-text-tertiary text-center pt-1">
                Forgot your password? Contact your system administrator.
              </p>
            </form>
          </div>

          <p className="text-[10px] text-text-tertiary text-center mt-6 tracking-wide">
            || Ganpati Bappa Morya ||
          </p>
        </div>
      </div>
    </div>
  );
};
