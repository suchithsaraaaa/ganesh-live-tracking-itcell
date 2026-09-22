import React from 'react';
import { DashboardKPIs } from '../types';
import { Activity, Navigation, PauseCircle, Waves, CheckCircle2, AlertTriangle, Database, UserX } from 'lucide-react';

interface KpiCardsProps {
  kpis: DashboardKPIs | null;
  selectedStateFilter: string;
  onSelectStateFilter: (state: string) => void;
}

export const KpiCards: React.FC<KpiCardsProps> = ({
  kpis,
  selectedStateFilter,
  onSelectStateFilter,
}) => {
  const cards = [
    {
      id: 'ALL',
      label: 'Total Registered',
      value: kpis?.total_idols ?? '...',
      icon: Database,
      color: 'text-blue-400',
      bgColor: 'bg-blue-950/40',
      borderColor: 'border-blue-900/50',
    },
    {
      id: 'TRACKING_ACTIVE',
      label: 'Tracking Active',
      value: kpis?.tracking_active ?? '...',
      icon: Activity,
      color: 'text-sky-400',
      bgColor: 'bg-sky-950/40',
      borderColor: 'border-sky-900/50',
    },
    {
      id: 'MOVING',
      label: 'In Transit (Moving)',
      value: kpis?.moving ?? '...',
      icon: Navigation,
      color: 'text-emerald-400',
      bgColor: 'bg-emerald-950/40',
      borderColor: 'border-emerald-900/50',
    },
    {
      id: 'HOLDING',
      label: 'Holding / Stop',
      value: kpis?.holding ?? '...',
      icon: PauseCircle,
      color: 'text-amber-400',
      bgColor: 'bg-amber-950/40',
      borderColor: 'border-amber-900/50',
    },
    {
      id: 'AT_VISARJAN',
      label: 'At Visarjan Site',
      value: kpis?.at_visarjan ?? '...',
      icon: Waves,
      color: 'text-purple-400',
      bgColor: 'bg-purple-950/40',
      borderColor: 'border-purple-900/50',
    },
    {
      id: 'IMMERSION_COMPLETED',
      label: 'Immersion Done',
      value: kpis?.immersion_completed ?? '...',
      icon: CheckCircle2,
      color: 'text-slate-400',
      bgColor: 'bg-slate-900/40',
      borderColor: 'border-slate-800',
    },
    {
      id: 'DEGRADED_OFFLINE',
      label: 'Offline / Degraded',
      value: kpis?.offline_or_degraded ?? '...',
      icon: AlertTriangle,
      color: 'text-rose-400',
      bgColor: 'bg-rose-950/40',
      borderColor: 'border-rose-900/50',
    },
    {
      id: 'UNASSIGNED',
      label: 'Unassigned',
      value: kpis?.unassigned ?? '...',
      icon: UserX,
      color: 'text-yellow-400',
      bgColor: 'bg-yellow-950/40',
      borderColor: 'border-yellow-900/50',
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-2 p-2 bg-slate-950 border-b border-slate-800 shrink-0">
      {cards.map((c) => {
        const Icon = c.icon;
        const isSelected = selectedStateFilter === c.id;
        return (
          <button
            key={c.id}
            onClick={() => onSelectStateFilter(isSelected ? 'ALL' : c.id)}
            className={`p-2.5 rounded-md border text-left transition-all cursor-pointer flex flex-col justify-between ${
              isSelected
                ? `${c.bgColor} ${c.borderColor} ring-2 ring-blue-500 shadow-lg`
                : 'bg-slate-900/70 border-slate-800 hover:border-slate-700 hover:bg-slate-900'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-[11px] font-medium text-slate-400 truncate pr-1">
                {c.label}
              </span>
              <Icon className={`w-3.5 h-3.5 ${c.color} shrink-0`} />
            </div>
            <div className={`text-lg font-bold mono ${c.color}`}>
              {c.value}
            </div>
          </button>
        );
      })}
    </div>
  );
};
