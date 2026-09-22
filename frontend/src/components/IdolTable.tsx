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

const STATE_BADGES: Record<ProcessionState, string> = {
  NOT_STARTED: 'bg-slate-800 text-slate-300 border-slate-700',
  TRACKING: 'bg-blue-950 text-blue-400 border-blue-800',
  MOVING: 'bg-emerald-950 text-emerald-400 border-emerald-800',
  HOLDING: 'bg-amber-950 text-amber-400 border-amber-800',
  AT_VISARJAN: 'bg-purple-950 text-purple-400 border-purple-800',
  IMMERSION_COMPLETED: 'bg-slate-900 text-slate-400 border-slate-800',
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
    <div className="flex flex-col h-full bg-slate-950 text-xs overflow-hidden border-t border-slate-800">
      {/* Table Action Bar / Pagination Summary */}
      <div className="px-4 py-2 bg-slate-900 border-b border-slate-800 flex items-center justify-between shrink-0">
        <div className="text-slate-400 text-xs">
          Showing <span className="text-white font-semibold">{idols.length}</span> of{' '}
          <span className="text-white font-semibold">{totalCount.toLocaleString()}</span> registered idols
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => loadData(currentPage - 1)}
            disabled={currentPage <= 1 || loading}
            className="p-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-300 transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="text-slate-300 mono text-[11px]">
            Page {currentPage} of {totalPages}
          </span>
          <button
            onClick={() => loadData(currentPage + 1)}
            disabled={currentPage >= totalPages || loading}
            className="p-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-300 transition-colors"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Table Container */}
      <div className="flex-1 overflow-auto">
        {loading ? (
          <div className="flex items-center justify-center h-48 text-slate-400">
            Loading authoritative idols registry...
          </div>
        ) : error ? (
          <div className="flex items-center justify-center h-48 text-rose-400">
            {error}
          </div>
        ) : (
          <table className="w-full border-collapse text-left">
            <thead className="bg-slate-900 text-slate-400 sticky top-0 border-b border-slate-800 text-[11px] uppercase tracking-wider font-semibold z-10">
              <tr>
                <th className="py-2.5 px-3">GPID</th>
                <th className="py-2.5 px-3">Idol / Pandal Name</th>
                <th className="py-2.5 px-3">Zone</th>
                <th className="py-2.5 px-3">Police Station</th>
                <th className="py-2.5 px-3">Procession Status</th>
                <th className="py-2.5 px-3">Immersion Waterbody</th>
                <th className="py-2.5 px-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-medium">
              {idols.map((idol) => {
                const isSelected = selectedGpid === idol.gpid;
                const badgeStyle = STATE_BADGES[idol.procession_state] || STATE_BADGES.NOT_STARTED;
                return (
                  <tr
                    key={idol.id}
                    onClick={() => onSelectIdol(idol)}
                    className={`cursor-pointer transition-colors ${
                      isSelected
                        ? 'bg-blue-950/70 border-l-4 border-l-blue-500'
                        : 'hover:bg-slate-900/80'
                    }`}
                  >
                    <td className="py-2 px-3 mono font-bold text-blue-400">
                      {idol.gpid}
                    </td>
                    <td className="py-2 px-3 text-slate-200">
                      <div className="truncate max-w-[200px] font-semibold">{idol.name}</div>
                      <div className="text-[10px] text-slate-400 truncate max-w-[200px]">
                        {idol.association_name || 'Individual'}
                      </div>
                    </td>
                    <td className="py-2 px-3 text-slate-300">{idol.zone}</td>
                    <td className="py-2 px-3 text-slate-300">
                      <span>{idol.police_station}</span>
                      <span className="text-[10px] mono text-slate-500 ml-1">({idol.ps_code})</span>
                    </td>
                    <td className="py-2 px-3">
                      <span className={`px-2 py-0.5 rounded border text-[10px] font-semibold ${badgeStyle}`}>
                        {idol.procession_state}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-slate-400 truncate max-w-[150px]">
                      {idol.river_name || 'Hussain Sagar'}
                    </td>
                    <td className="py-2 px-3 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectIdol(idol);
                        }}
                        className="p-1 rounded bg-slate-800 hover:bg-blue-600 text-slate-300 hover:text-white transition-colors"
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
