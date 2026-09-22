import React from 'react';
import { Link } from 'react-router-dom';
import { Compass } from 'lucide-react';

export const NotFoundPage: React.FC = () => (
  <div className="h-screen w-screen flex flex-col items-center justify-center gap-4 bg-base animate-fade-in-up">
    <Compass className="w-10 h-10 text-text-tertiary" strokeWidth={1.5} />
    <div className="text-center">
      <h1 className="text-lg font-semibold text-text-primary">Page Not Found</h1>
      <p className="text-sm text-text-tertiary mt-1">The page you&apos;re looking for doesn&apos;t exist.</p>
    </div>
    <Link
      to="/"
      className="px-4 py-2 rounded-md bg-elevated-2 border border-border-default text-sm text-text-secondary hover:text-text-primary hover:border-accent/40 transition-colors"
    >
      Return to Dashboard
    </Link>
  </div>
);
