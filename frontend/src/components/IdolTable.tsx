import React, { useEffect, useState } from 'react';
import { Idol, ProcessionState } from '../types';
import { fetchIdols } from '../api/client';
import { ChevronLeft, ChevronRight, Eye } from 'lucide-react';

interface IdolTableProps {
  searchTerm: string;
  selectedZone: string;
  selectedPs: string;
  selectedStateFilter: string;
  selectedGpid: string | null;
  onSelectIdol: (idol: Idol) => void;
}

const STATE_COLOR: Record<ProcessionState, string> = {
  NOT_STARTED: 'var(--color-status-neutral)',
  TRACKING: 'var(--color-status-tracking)',
  MOVING: 'var(--color-status-active)',
  HOLDING: 'var(--color-status-warning)',
  AT_VISARJAN: 'var(--color-status-visarjan)',
  IMMERSION_COMPLETED: 'var(--color-status-neutral)',
};

export const IdolTable: React.FC<IdolTableProps> = ({
  searchTerm,
  selectedZone,
  selectedPs,
  selectedStateFilter,
  selectedGpid,
  onSelectIdol,
}) => {
  const [idols, setIdols] = useState<Idol[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = async (page: number) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchIdols({
        search: searchTerm || undefined,
        zone: selectedZone !== 'All Zones' ? selectedZone : undefined,
        police_station: selectedPs || undefined,
        procession_state: selectedStateFilter !== 'ALL' ? selectedStateFilter : undefined,
        page,
      });
      setIdols(data.results);
      setTotalCount(data.count);
      setCurrentPage(page);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch idols table.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setCurrentPage(1);
    loadData(1);
  }, [searchTerm, selectedZone, selectedPs, selectedStateFilter]);

  const totalPages = Math.ceil(totalCount / 50) || 1;

  return (
    <div className="flex flex-col h-full bg-base text-xs overflow-hidden border-t border-border-subtle">
      {/* Action bar / pagination summary */}
      <div className="px-4 py-2 bg-base border-b border-border-subtle flex items-center justify-between shrink-0">
        <div className="text-text-tertiary text-[11px]">
          Showing <span className="text-text-primary font-medium">{idols.length}</span> of{' '}
          <span className="text-text-primary font-medium">{totalCount.toLocaleString()}</span> registered GPIDs
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => loadData(currentPage - 1)}
            disabled={currentPage <= 1 || loading}
            className="p-1 rounded bg-elevated-2 hover:bg-border-default/40 disabled:opacity-40 text-text-secondary transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="text-text-secondary mono text-[11px]">
            Page {currentPage} of {totalPages}
          </span>
          <button
            onClick={() => loadData(currentPage + 1)}
            disabled={currentPage >= totalPages || loading}
            className="p-1 rounded bg-elevated-2 hover:bg-border-default/40 disabled:opacity-40 text-text-secondary transition-colors"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-auto">
        {loading ? (
          <div className="flex items-center justify-center h-48 text-text-tertiary">
            Loading authoritative GPID registry…
          </div>
        ) : error ? (
          <div className="flex items-center justify-center h-48 text-status-critical">
            {error}
          </div>
        ) : idols.length === 0 ? (
          <div className="flex items-center justify-center h-48 text-text-tertiary">
            No GPIDs match the current filters
          </div>
        ) : (
          <table className="w-full border-collapse text-left">
            <thead className="bg-base text-text-tertiary sticky top-0 border-b border-border-subtle text-[10px] uppercase tracking-wider font-medium z-10">
              <tr>
                <th className="py-2.5 px-3">GPID</th>
                <th className="py-2.5 px-3">Idol / Pandal Name</th>
                <th className="py-2.5 px-3">Zone</th>
                <th className="py-2.5 px-3">Police Station</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3">Immersion Waterbody</th>
                <th className="py-2.5 px-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-subtle">
              {idols.map((idol) => {
                const isSelected = selectedGpid === idol.gpid;
                const color = STATE_COLOR[idol.procession_state] || STATE_COLOR.NOT_STARTED;
                return (
                  <tr
                    key={idol.id}
                    onClick={() => onSelectIdol(idol)}
                    className={`cursor-pointer transition-colors ${
                      isSelected ? 'bg-elevated-2' : 'hover:bg-elevated/60'
                    }`}
                  >
                    <td className="py-2 px-3 mono font-medium text-text-primary">
                      {idol.gpid}
                    </td>
                    <td className="py-2 px-3 text-text-secondary">
                      <div className="truncate max-w-[200px] font-medium text-text-primary">{idol.name}</div>
                      <div className="text-[10px] text-text-tertiary truncate max-w-[200px]">
                        {idol.association_name || 'Individual'}
                      </div>
                    </td>
                    <td className="py-2 px-3 text-text-secondary">{idol.zone}</td>
                    <td className="py-2 px-3 text-text-secondary">
                      <span>{idol.police_station}</span>
                      <span className="text-[10px] mono text-text-tertiary ml-1">({idol.ps_code})</span>
                    </td>
                    <td className="py-2 px-3">
                      <span className="text-[10px] font-medium uppercase tracking-wide" style={{ color }}>
                        {idol.procession_state.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-text-tertiary truncate max-w-[150px]">
                      {idol.river_name || 'Hussain Sagar'}
                    </td>
                    <td className="py-2 px-3 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectIdol(idol);
                        }}
                        className="p-1 rounded bg-elevated-2 hover:bg-accent hover:text-base text-text-secondary transition-colors"
                        title="Focus on Map"
                      >
                        <Eye className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};
