import React from 'react';
import { DashboardKPIs } from '../types';

interface KpiCardsProps {
  kpis: DashboardKPIs | null;
  selectedStateFilter: string;
  onSelectStateFilter: (state: string) => void;
}

interface Metric {
  id: string;
  label: string;
  value: number | undefined;
  colorVar: string;
}

export const KpiCards: React.FC<KpiCardsProps> = ({
  kpis,
  selectedStateFilter,
  onSelectStateFilter,
}) => {
  const metrics: Metric[] = [
    { id: 'ALL', label: 'Total GPIDs', value: kpis?.total_idols, colorVar: 'var(--color-text-primary)' },
    { id: 'TRACKING_ACTIVE', label: 'Active Tracking', value: kpis?.tracking_active, colorVar: 'var(--color-status-tracking)' },
    { id: 'MOVING', label: 'Moving', value: kpis?.moving, colorVar: 'var(--color-status-active)' },
    { id: 'HOLDING', label: 'In Holding', value: kpis?.holding, colorVar: 'var(--color-status-warning)' },
    { id: 'AT_VISARJAN', label: 'At Visarjan', value: kpis?.at_visarjan, colorVar: 'var(--color-status-visarjan)' },
    { id: 'IMMERSION_COMPLETED', label: 'Immersed', value: kpis?.immersion_completed, colorVar: 'var(--color-status-neutral)' },
    { id: 'DEGRADED_OFFLINE', label: 'Offline / Degraded', value: kpis?.offline_or_degraded, colorVar: 'var(--color-status-critical)' },
    { id: 'UNASSIGNED', label: 'Unassigned', value: kpis?.unassigned, colorVar: 'var(--color-status-warning)' },
  ];

  return (
    <div className="flex flex-wrap items-stretch bg-base border-b border-border-subtle px-6 py-4 shrink-0 gap-x-0 gap-y-3">
      {metrics.map((m, i) => {
        const isSelected = selectedStateFilter === m.id;
        return (
          <button
            key={m.id}
            type="button"
            onClick={() => onSelectStateFilter(isSelected ? 'ALL' : m.id)}
            className={`text-left pr-8 ${i > 0 ? 'pl-8 border-l border-border-subtle' : ''} ${
              isSelected ? 'opacity-100' : 'opacity-90 hover:opacity-100'
            } transition-opacity`}
          >
            <div
              className="text-[28px] leading-none font-semibold tracking-tight mono"
              style={{ color: isSelected ? 'var(--color-accent)' : m.colorVar }}
            >
              {m.value !== undefined ? m.value.toLocaleString() : '–'}
            </div>
            <div className="text-[10px] font-medium tracking-wider uppercase text-text-secondary mt-1.5">
              {m.label}
            </div>
          </button>
        );
      })}
    </div>
  );
};
