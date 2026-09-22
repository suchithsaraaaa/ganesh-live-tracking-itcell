import React, { useMemo } from 'react';
import { Waves } from 'lucide-react';
import { useIdolsByState } from '../hooks/useIdolsByState';
import { useTracking } from '../context/TrackingContext';
import { LoadingState, EmptyState, ErrorState } from '../components/shared/States';

export const VisarjanPointsPage: React.FC = () => {
  const { idols, loading, error, reload } = useIdolsByState('AT_VISARJAN');
  const { handleSelectIdol } = useTracking();

  const byWaterbody = useMemo(() => {
    const map = new Map<string, typeof idols>();
    idols.forEach((idol) => {
      const key = idol.river_name || 'Unspecified waterbody';
      const arr = map.get(key) || [];
      arr.push(idol);
      map.set(key, arr);
    });
    return Array.from(map.entries()).sort((a, b) => b[1].length - a[1].length);
  }, [idols]);

  return (
    <div className="h-full flex flex-col overflow-hidden animate-fade-in-up">
      <div className="px-6 pt-6 pb-4">
        <h1 className="text-lg font-semibold text-text-primary">Visarjan Points</h1>
        <p className="text-xs text-text-tertiary mt-0.5">
          GPIDs currently at a visarjan (immersion) site, grouped by destination waterbody.
        </p>
      </div>

      <div className="flex-1 overflow-y-auto px-6 pb-6">
        {loading && <LoadingState label="Loading visarjan-site GPIDs…" />}
        {!loading && error && <ErrorState message={error} onRetry={reload} />}
        {!loading && !error && idols.length === 0 && (
          <EmptyState title="No GPIDs are currently at a visarjan site" />
        )}
        {!loading && !error && byWaterbody.length > 0 && (
          <div className="space-y-4">
            {byWaterbody.map(([waterbody, group]) => (
              <div key={waterbody} className="bg-elevated border border-border-subtle rounded-lg overflow-hidden">
                <div className="flex items-center gap-2 px-4 py-2.5 border-b border-border-subtle bg-elevated-2/40">
                  <Waves className="w-4 h-4 text-status-visarjan" strokeWidth={1.8} />
                  <span className="text-sm font-medium text-text-primary">{waterbody}</span>
                  <span className="text-[11px] mono text-text-tertiary ml-auto">{group.length} GPID{group.length !== 1 ? 's' : ''}</span>
                </div>
                {group.map((idol, i) => (
                  <button
                    key={idol.id}
                    onClick={() => handleSelectIdol(idol)}
                    className={`w-full flex items-center gap-3 px-4 py-2.5 text-left text-xs transition-colors hover:bg-elevated-2/60 ${i > 0 ? 'border-t border-border-subtle' : ''}`}
                  >
                    <span className="mono font-medium text-text-primary w-48 truncate">{idol.gpid}</span>
                    <span className="text-text-secondary flex-1 truncate">{idol.name || idol.association_name}</span>
                    <span className="text-text-tertiary">{idol.police_station}</span>
                  </button>
                ))}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
