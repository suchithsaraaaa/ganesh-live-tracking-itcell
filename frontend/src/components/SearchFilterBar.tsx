import React from 'react';
import { Search, X } from 'lucide-react';

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
    <div className="flex flex-wrap items-center gap-2.5 px-6 py-3 bg-base border-b border-border-subtle text-xs shrink-0">
      <div className="relative flex-1 min-w-[240px]">
        <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-text-tertiary" />
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search GPID, Police Station, Zone, Location…"
          className="w-full pl-8 pr-3 py-2 bg-elevated-2 border border-border-default rounded-md text-text-primary placeholder-text-tertiary focus:outline-none focus:border-accent mono text-[12px]"
        />
        {searchTerm && (
          <button
            onClick={() => onSearchChange('')}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-text-tertiary hover:text-text-primary"
          >
            <X className="w-3 h-3" />
          </button>
        )}
      </div>

      <select
        value={selectedZone}
        onChange={(e) => onZoneChange(e.target.value)}
        className="bg-elevated-2 border border-border-default rounded-md px-2.5 py-2 text-text-secondary focus:outline-none focus:border-accent"
      >
        {ZONES.map((z) => (
          <option key={z} value={z}>{z}</option>
        ))}
      </select>

      <input
        type="text"
        value={selectedPs}
        onChange={(e) => onPsChange(e.target.value)}
        placeholder="Police Station…"
        className="w-44 px-2.5 py-2 bg-elevated-2 border border-border-default rounded-md text-text-secondary placeholder-text-tertiary focus:outline-none focus:border-accent"
      />

      {hasFilters && (
        <button
          onClick={onClear}
          className="px-3 py-2 bg-elevated-2 hover:bg-border-default/40 border border-border-default text-text-secondary rounded-md flex items-center gap-1.5 transition-colors"
        >
          <X className="w-3 h-3" />
          <span>Reset</span>
        </button>
      )}
    </div>
  );
};
