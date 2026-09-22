import React from 'react';
import { Link } from 'react-router-dom';
import { ShieldAlert } from 'lucide-react';

export const AccessDeniedPage: React.FC = () => (
  <div className="h-full flex flex-col items-center justify-center gap-4 animate-fade-in-up">
    <ShieldAlert className="w-10 h-10 text-status-critical" strokeWidth={1.5} />
    <div className="text-center">
      <h1 className="text-lg font-semibold text-text-primary">Access Restricted</h1>
      <p className="text-sm text-text-tertiary mt-1 max-w-sm">
        You don&apos;t have permission to access this module.
      </p>
    </div>
    <Link
      to="/"
      className="px-4 py-2 rounded-md bg-elevated-2 border border-border-default text-sm text-text-secondary hover:text-text-primary hover:border-accent/40 transition-colors"
    >
      Return to Dashboard
    </Link>
  </div>
);
