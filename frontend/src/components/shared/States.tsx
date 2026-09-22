import React from 'react';
import { AlertTriangle, Inbox, RotateCw } from 'lucide-react';

export const LoadingState: React.FC<{ label?: string; className?: string }> = ({ label = 'Loading…', className = '' }) => (
  <div className={`flex flex-col items-center justify-center gap-3 py-16 text-text-tertiary ${className}`}>
    <div className="flex gap-1.5">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="w-1.5 h-1.5 rounded-full bg-accent/70"
          style={{ animation: `pulse-dot 1.1s ${i * 0.15}s infinite ease-in-out` }}
        />
      ))}
    </div>
    <span className="text-xs">{label}</span>
  </div>
);

export const EmptyState: React.FC<{ title: string; hint?: string; className?: string }> = ({ title, hint, className = '' }) => (
  <div className={`flex flex-col items-center justify-center gap-2 py-16 text-center ${className}`}>
    <Inbox className="w-6 h-6 text-text-tertiary" strokeWidth={1.5} />
    <p className="text-sm text-text-secondary">{title}</p>
    {hint && <p className="text-xs text-text-tertiary max-w-xs">{hint}</p>}
  </div>
);

export const ErrorState: React.FC<{ message: string; onRetry?: () => void; className?: string }> = ({ message, onRetry, className = '' }) => (
  <div className={`flex flex-col items-center justify-center gap-3 py-16 text-center ${className}`}>
    <AlertTriangle className="w-6 h-6 text-status-critical" strokeWidth={1.5} />
    <p className="text-sm text-status-critical max-w-sm">{message}</p>
    {onRetry && (
      <button
        onClick={onRetry}
        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-elevated-2 border border-border-default text-text-secondary hover:text-text-primary hover:border-accent/40 transition-colors"
      >
        <RotateCw className="w-3.5 h-3.5" />
        Retry
      </button>
    )}
  </div>
);
