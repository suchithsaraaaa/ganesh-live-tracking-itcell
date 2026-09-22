import React from 'react';
import { Search, Filter, X } from 'lucide-react';

interface SearchFilterBarProps {
  searchTerm: string;
  onSearchChange: (val: string) => void;
  selectedZone: string;
  onZoneChange: (zone: string) => void;
  selectedPs: string;
  onPsChange: (ps: string) => void;
  onClear: () => void;
}

const ZONES = [
  'All Zones',
  'Charminar',
  'Secunderabad',
  'Shamshabad',
  'Golconda',
  'Jubilee Hills',
  'Khairatabad',
  'Rajendranagar',
];

export const SearchFilterBar: React.FC<SearchFilterBarProps> = ({
  searchTerm,
  onSearchChange,
  selectedZone,
  onZoneChange,
  selectedPs,
  onPsChange,
  onClear,
}) => {
  const hasFilters = searchTerm || selectedZone !== 'All Zones' || selectedPs;

  return (
    <div className="flex flex-wrap items-center gap-2 p-2 bg-slate-900 border-b border-slate-800 text-xs shrink-0">
      {/* Search Input */}
      <div className="relative flex-1 min-w-[220px]">
        <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500" />
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search by GPID (e.g. HYDCMRZCMNR1749), Name, PS..."
          className="w-full pl-8 pr-3 py-1.5 bg-slate-950 border border-slate-800 rounded text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 mono"
        />
        {searchTerm && (
          <button
            onClick={() => onSearchChange('')}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
          >
            <X className="w-3 h-3" />
          </button>
        )}
      </div>

      {/* Zone Filter */}
      <div className="flex items-center space-x-1.5">
        <Filter className="w-3.5 h-3.5 text-slate-400" />
        <select
          value={selectedZone}
          onChange={(e) => onZoneChange(e.target.value)}
          className="bg-slate-950 border border-slate-800 rounded px-2 py-1.5 text-slate-300 focus:outline-none focus:border-blue-500"
        >
          {ZONES.map((z) => (
            <option key={z} value={z}>{z}</option>
          ))}
        </select>
      </div>

      {/* PS Filter Input */}
      <div className="w-40">
        <input
          type="text"
          value={selectedPs}
          onChange={(e) => onPsChange(e.target.value)}
          placeholder="Filter Police Station..."
          className="w-full px-2.5 py-1.5 bg-slate-950 border border-slate-800 rounded text-slate-300 placeholder-slate-500 focus:outline-none focus:border-blue-500"
        />
      </div>

      {/* Reset button */}
      {hasFilters && (
        <button
          onClick={onClear}
          className="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded flex items-center space-x-1 transition-colors"
        >
          <X className="w-3 h-3" />
          <span>Reset Filters</span>
        </button>
      )}
    </div>
  );
};
