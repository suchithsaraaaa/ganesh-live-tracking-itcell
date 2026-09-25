import React from 'react';
import { Search, X, Calendar } from 'lucide-react';

interface SearchFilterBarProps {
  searchTerm: string;
  onSearchChange: (val: string) => void;
  selectedZone: string;
  onZoneChange: (zone: string) => void;
  selectedPs: string;
  onPsChange: (ps: string) => void;
  selectedHeightBucket?: string;
  onHeightBucketChange?: (bucket: string) => void;
  isImmersionsToday?: boolean;
  onImmersionsTodayChange?: (val: boolean) => void;
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
  'Rajendra Nagar',
];

export const SearchFilterBar: React.FC<SearchFilterBarProps> = ({
  searchTerm,
  onSearchChange,
  selectedZone,
  onZoneChange,
  selectedPs,
  onPsChange,
  selectedHeightBucket = 'ALL',
  onHeightBucketChange,
  isImmersionsToday = false,
  onImmersionsTodayChange,
  onClear,
}) => {
  const hasFilters =
    searchTerm ||
    selectedZone !== 'All Zones' ||
    selectedPs ||
    selectedHeightBucket !== 'ALL' ||
    isImmersionsToday;

  return (
    <div className="flex flex-wrap items-center gap-2.5 px-6 py-3 bg-base border-b border-border-subtle text-xs shrink-0">
      <div className="relative flex-1 min-w-[220px]">
        <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-text-tertiary" />
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search GPID (>=15ft), Station, Zone…"
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

      {onHeightBucketChange && (
        <div className="flex items-center space-x-1">
          <select
            value={selectedHeightBucket}
            onChange={(e) => onHeightBucketChange(e.target.value)}
            className="bg-elevated-2 border border-border-default rounded-md px-2.5 py-2 text-text-secondary focus:outline-none focus:border-accent font-medium"
            title="Height Classification"
          >
            <option value="ALL">All Heights</option>
            <option value="below_15">Below 15 FT</option>
            <option value="15_20">15–20 FT (Green)</option>
            <option value="21_25">21–25 FT (Yellow)</option>
            <option value="above_25">26+ FT (Red)</option>
          </select>
        </div>
      )}

      {onImmersionsTodayChange && (
        <button
          type="button"
          onClick={() => onImmersionsTodayChange(!isImmersionsToday)}
          className={`px-3 py-2 rounded-md border flex items-center space-x-1.5 transition-all font-medium ${
            isImmersionsToday
              ? 'bg-amber-500/20 text-amber-300 border-amber-500/50 shadow-sm shadow-amber-500/10'
              : 'bg-elevated-2 text-text-secondary border-border-default hover:text-text-primary hover:border-border-subtle'
          }`}
          title="Filter idols with immersion scheduled for today"
        >
          <Calendar className="w-3.5 h-3.5" />
          <span>Immersions Today</span>
          {isImmersionsToday && (
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse ml-0.5" />
          )}
        </button>
      )}

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
        className="w-36 px-2.5 py-2 bg-elevated-2 border border-border-default rounded-md text-text-secondary placeholder-text-tertiary focus:outline-none focus:border-accent"
      />

      {hasFilters && (
        <button
          onClick={onClear}
          className="px-3 py-2 bg-elevated-2 hover:bg-border-default/40 border border-border-default text-text-secondary rounded-md flex items-center gap-1.5 transition-colors"
          title="Reset all filters"
        >
          <X className="w-3 h-3" />
          <span>Reset</span>
        </button>
      )}
    </div>
  );
};
