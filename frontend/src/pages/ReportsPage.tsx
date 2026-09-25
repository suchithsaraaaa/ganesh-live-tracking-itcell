import React, { useEffect, useState, useMemo, useCallback } from 'react';
import {
  Search,
  FileDown,
  FileText,
  ChevronLeft,
  ChevronRight,
  RotateCcw,
  CheckCircle2,
  Clock,
} from 'lucide-react';
import { CompletedReportItem, CompletedReportsSummary, PoliceStationMaster } from '../types';
import {
  fetchAuthoritativePoliceStations,
  fetchCompletedReportsRegistry,
  getReportDownloadUrl,
} from '../api/client';
import { LoadingState, EmptyState, ErrorState } from '../components/shared/States';

type HeightBucketFilter = 'all' | 'all_15_plus' | '15_20' | '21_25' | '26_plus' | 'below_15';
type VisarjanDateFilter = 'all' | 'today' | 'tomorrow' | 'custom';
type OperationalStatusFilter = 'all' | 'completed' | 'holding';

export const ReportsPage: React.FC = () => {
  // Filter States
  const [selectedZone, setSelectedZone] = useState<string>('All Zones');
  const [selectedStation, setSelectedStation] = useState<string>('All Police Stations');
  const [selectedHeight, setSelectedHeight] = useState<HeightBucketFilter>('all');
  const [visarjanDateMode, setVisarjanDateMode] = useState<VisarjanDateFilter>('all');
  const [customVisarjanDate, setCustomVisarjanDate] = useState<string>('');
  const [operationalStatus, setOperationalStatus] = useState<OperationalStatusFilter>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [debouncedSearch, setDebouncedSearch] = useState<string>('');

  // Pagination & Data States
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize] = useState<number>(25);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [reports, setReports] = useState<CompletedReportItem[]>([]);
  const [summary, setSummary] = useState<CompletedReportsSummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Authoritative Police Stations
  const [policeStations, setPoliceStations] = useState<PoliceStationMaster[]>([]);

  // Debounce search input (300ms)
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery);
      setCurrentPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Load authoritative police stations for cascading dropdowns
  useEffect(() => {
    fetchAuthoritativePoliceStations()
      .then((data) => setPoliceStations(data.results || []))
      .catch(() => {});
  }, []);

  // Compute available zones from authoritative police stations
  const availableZones = useMemo(() => {
    const zones = new Set<string>();
    policeStations.forEach((ps) => {
      if (ps.zone) zones.add(ps.zone);
    });
    return Array.from(zones).sort();
  }, [policeStations]);

  // Compute cascading police stations based on selectedZone
  const availableStations = useMemo(() => {
    if (!selectedZone || selectedZone === 'All Zones') {
      return policeStations.map((ps) => ps.ps_name).sort();
    }
    const cleanSelected = selectedZone.replace(/\s+/g, '').toLowerCase();
    return policeStations
      .filter((ps) => (ps.zone || '').replace(/\s+/g, '').toLowerCase() === cleanSelected)
      .map((ps) => ps.ps_name)
      .sort();
  }, [policeStations, selectedZone]);

  // Reset station if selected zone no longer includes it
  const handleZoneChange = (zone: string) => {
    setSelectedZone(zone);
    setSelectedStation('All Police Stations');
    setCurrentPage(1);
  };

  // Authoritative Visarjan Date computation
  const computedVisarjanDate = useMemo(() => {
    if (visarjanDateMode === 'today') return 'today';
    if (visarjanDateMode === 'tomorrow') return 'tomorrow';
    if (visarjanDateMode === 'custom' && customVisarjanDate) return customVisarjanDate;
    return undefined;
  }, [visarjanDateMode, customVisarjanDate]);

  // Primary Data Fetcher for Completed Reports Registry
  const loadReports = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchCompletedReportsRegistry({
        page: currentPage,
        page_size: pageSize,
        search: debouncedSearch.trim() || undefined,
        zone: selectedZone !== 'All Zones' ? selectedZone : undefined,
        police_station: selectedStation !== 'All Police Stations' ? selectedStation : undefined,
        height_bucket: selectedHeight !== 'all' ? selectedHeight : undefined,
        operational_status: operationalStatus !== 'all' ? operationalStatus : undefined,
        visarjan_date: computedVisarjanDate,
      });

      setReports(data.results || []);
      setTotalCount(data.count || 0);
      setSummary(data.summary || null);
    } catch (err: any) {
      setError(err.message || 'Failed to load completed reports registry');
      setReports([]);
    } finally {
      setLoading(false);
    }
  }, [
    currentPage,
    pageSize,
    debouncedSearch,
    selectedZone,
    selectedStation,
    selectedHeight,
    operationalStatus,
    computedVisarjanDate,
  ]);

  useEffect(() => {
    loadReports();
  }, [loadReports]);

  // Check if any filter is actively applied
  const isFiltered = useMemo(() => {
    return (
      selectedZone !== 'All Zones' ||
      selectedStation !== 'All Police Stations' ||
      selectedHeight !== 'all' ||
      operationalStatus !== 'all' ||
      visarjanDateMode !== 'all' ||
      Boolean(searchQuery.trim())
    );
  }, [selectedZone, selectedStation, selectedHeight, operationalStatus, visarjanDateMode, searchQuery]);

  const handleResetFilters = () => {
    setSelectedZone('All Zones');
    setSelectedStation('All Police Stations');
    setSelectedHeight('all');
    setOperationalStatus('all');
    setVisarjanDateMode('all');
    setCustomVisarjanDate('');
    setSearchQuery('');
    setDebouncedSearch('');
    setCurrentPage(1);
  };

  const totalPages = Math.ceil(totalCount / pageSize) || 1;

  return (
    <div className="h-full flex flex-col overflow-hidden animate-fade-in-up bg-base">
      {/* Header Bar */}
      <div className="px-6 py-4 border-b border-border-subtle bg-elevated-1/80 shrink-0 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2.5">
            <div className="p-1.5 rounded-md bg-accent/15 border border-accent/30 text-accent">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-text-primary tracking-tight">
                Procession Reports Registry
              </h1>
              <p className="text-xs text-text-tertiary">
                Authoritative operational reports for GPIDs that have concluded visarjan or reached holding stages.
              </p>
            </div>
          </div>
        </div>

        {/* Quick Stats / Refresh */}
        <div className="flex items-center space-x-3">
          <button
            onClick={loadReports}
            disabled={loading}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded bg-elevated border border-border-default text-text-secondary hover:text-text-primary text-xs font-semibold transition-colors cursor-pointer disabled:opacity-50"
            title="Refresh reports registry"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Filter / Control Bar */}
      <div className="px-6 py-3 bg-base border-b border-border-subtle shrink-0">
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2.5 items-start">
          {/* Zone Filter */}
          <div>
            <label className="block text-[10px] uppercase font-bold text-text-tertiary mb-1">
              Zone
            </label>
            <select
              value={selectedZone}
              onChange={(e) => handleZoneChange(e.target.value)}
              className="w-full px-2.5 py-1.5 bg-elevated border border-border-default rounded text-xs text-text-primary focus:outline-none focus:border-accent"
            >
              <option value="All Zones">All Zones</option>
              {availableZones.map((z) => (
                <option key={z} value={z}>
                  {z}
                </option>
              ))}
            </select>
          </div>

          {/* Police Station Filter (Cascading) */}
          <div>
            <label className="block text-[10px] uppercase font-bold text-text-tertiary mb-1">
              Police Station
            </label>
            <select
              value={selectedStation}
              onChange={(e) => {
                setSelectedStation(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full px-2.5 py-1.5 bg-elevated border border-border-default rounded text-xs text-text-primary focus:outline-none focus:border-accent"
            >
              <option value="All Police Stations">All Police Stations</option>
              {availableStations.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>

          {/* Height Bucket Filter */}
          <div>
            <label className="block text-[10px] uppercase font-bold text-text-tertiary mb-1">
              Height Filter
            </label>
            <select
              value={selectedHeight}
              onChange={(e) => {
                setSelectedHeight(e.target.value as HeightBucketFilter);
                setCurrentPage(1);
              }}
              className="w-full px-2.5 py-1.5 bg-elevated border border-border-default rounded text-xs text-text-primary focus:outline-none focus:border-accent font-medium"
            >
              <option value="all">
                All Heights ({summary ? summary.total_eligible : '…'})
              </option>
              <option value="all_15_plus">
                All 15+ FT ({summary ? ((summary.count_15_20 || 0) + (summary.count_21_25 || 0) + (summary.count_26_plus || 0)) : '…'})
              </option>
              <option value="15_20">
                15–20 FT ({summary ? summary.count_15_20 : '…'})
              </option>
              <option value="21_25">
                21–25 FT ({summary ? summary.count_21_25 : '…'})
              </option>
              <option value="26_plus">
                26 FT+ ({summary ? summary.count_26_plus : '…'})
              </option>
              <option value="below_15">
                Under 15 FT ({summary && summary.count_below_15 !== undefined ? summary.count_below_15 : '…'})
              </option>
            </select>
          </div>

          {/* Visarjan Date Filter */}
          <div>
            <label className="block text-[10px] uppercase font-bold text-text-tertiary mb-1">
              Visarjan Date
            </label>
            <select
              value={visarjanDateMode}
              onChange={(e) => {
                setVisarjanDateMode(e.target.value as VisarjanDateFilter);
                setCurrentPage(1);
              }}
              className="w-full px-2.5 py-1.5 bg-elevated border border-border-default rounded text-xs text-text-primary focus:outline-none focus:border-accent font-medium"
            >
              <option value="all">All Dates</option>
              <option value="today">Today</option>
              <option value="tomorrow">Tomorrow</option>
              <option value="custom">Custom Date…</option>
            </select>
            {visarjanDateMode === 'custom' && (
              <input
                type="date"
                value={customVisarjanDate}
                onChange={(e) => {
                  setCustomVisarjanDate(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-full mt-1 px-2 py-1 bg-elevated border border-border-default rounded text-xs text-text-primary focus:outline-none focus:border-accent mono"
              />
            )}
          </div>

          {/* Operational Status Filter */}
          <div>
            <label className="block text-[10px] uppercase font-bold text-text-tertiary mb-1">
              Final Status
            </label>
            <select
              value={operationalStatus}
              onChange={(e) => {
                setOperationalStatus(e.target.value as OperationalStatusFilter);
                setCurrentPage(1);
              }}
              className="w-full px-2.5 py-1.5 bg-elevated border border-border-default rounded text-xs text-text-primary focus:outline-none focus:border-accent"
            >
              <option value="all">
                All Finished ({summary ? summary.total_eligible : '…'})
              </option>
              <option value="completed">
                Completed ({summary ? summary.count_completed : '…'})
              </option>
              <option value="holding">
                In Holding ({summary ? summary.count_holding : '…'})
              </option>
            </select>
          </div>

          {/* Search input & clear button */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="block text-[10px] uppercase font-bold text-text-tertiary">
                Search GPID / Organizer
              </label>
              {isFiltered && (
                <button
                  onClick={handleResetFilters}
                  className="text-[10px] text-accent hover:underline cursor-pointer"
                >
                  Reset Filters
                </button>
              )}
            </div>
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-text-tertiary" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search GPID, name, station…"
                className="w-full pl-8 pr-2.5 py-1.5 bg-elevated border border-border-default rounded text-xs text-text-primary focus:outline-none focus:border-accent mono"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Operational Summary Cards */}
      <div className="px-6 py-3.5 bg-elevated-1/50 border-b border-border-subtle shrink-0">
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
          {/* Total Eligible */}
          <div className="p-3 bg-elevated rounded border border-border-default shadow-sm">
            <div className="text-[10px] font-bold uppercase tracking-wider text-text-tertiary">
              TOTAL FINALIZED
            </div>
            <div className="text-xl font-bold text-text-primary mt-0.5 mono">
              {summary ? summary.total_eligible : '—'}
            </div>
            <div className="text-[10px] text-accent font-medium mt-0.5">
              {summary && summary.count_below_15 ? `Finished/Staged (incl. ${summary.count_below_15} <15 FT)` : 'Finished or Staged'}
            </div>
          </div>

          {/* Immersion Completed */}
          <div className="p-3 bg-emerald-950/20 rounded border border-emerald-500/25 shadow-sm">
            <div className="text-[10px] font-bold uppercase tracking-wider text-emerald-400">
              IMMERSION COMPLETED
            </div>
            <div className="text-xl font-bold text-emerald-300 mt-0.5 mono">
              {summary ? summary.count_completed : '—'}
            </div>
            <div className="text-[10px] text-emerald-400/80 font-medium mt-0.5">Visarjan Finalized</div>
          </div>

          {/* In Holding */}
          <div className="p-3 bg-amber-950/20 rounded border border-amber-500/25 shadow-sm">
            <div className="text-[10px] font-bold uppercase tracking-wider text-amber-400">
              IN HOLDING
            </div>
            <div className="text-xl font-bold text-amber-300 mt-0.5 mono">
              {summary ? summary.count_holding : '—'}
            </div>
            <div className="text-[10px] text-amber-400/80 font-medium mt-0.5">Staged Stoppage</div>
          </div>

          {/* 15-20 FT */}
          <div className="p-3 bg-emerald-950/10 rounded border border-border-default shadow-sm">
            <div className="text-[10px] font-bold uppercase tracking-wider text-emerald-400">
              15–20 FT
            </div>
            <div className="text-xl font-bold text-emerald-300 mt-0.5 mono">
              {summary ? summary.count_15_20 : '—'}
            </div>
            <div className="text-[10px] text-text-tertiary mt-0.5">Green Category</div>
          </div>

          {/* 21-25 FT */}
          <div className="p-3 bg-amber-950/10 rounded border border-border-default shadow-sm">
            <div className="text-[10px] font-bold uppercase tracking-wider text-amber-400">
              21–25 FT
            </div>
            <div className="text-xl font-bold text-amber-300 mt-0.5 mono">
              {summary ? summary.count_21_25 : '—'}
            </div>
            <div className="text-[10px] text-text-tertiary mt-0.5">Yellow Category</div>
          </div>

          {/* 26+ FT */}
          <div className="p-3 bg-rose-950/10 rounded border border-border-default shadow-sm">
            <div className="text-[10px] font-bold uppercase tracking-wider text-rose-400">
              26 FT+
            </div>
            <div className="text-xl font-bold text-rose-300 mt-0.5 mono">
              {summary ? summary.count_26_plus : '—'}
            </div>
            <div className="text-[10px] text-text-tertiary mt-0.5">Red Category</div>
          </div>
        </div>
      </div>

      {/* Main Table Content */}
      <div className="flex-1 overflow-auto px-6 py-4">
        {loading ? (
          <LoadingState label="Loading finalized reports registry…" />
        ) : error ? (
          <ErrorState message={error} />
        ) : reports.length === 0 ? (
          <EmptyState
            title="No qualifying reports found"
            hint={
              isFiltered
                ? 'Try adjusting your filters or search terms.'
                : 'Reports only include GPIDs that have concluded visarjan or reached holding status.'
            }
          />
        ) : (
          <div className="border border-border-subtle rounded-lg bg-elevated overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-elevated-1 border-b border-border-subtle text-text-tertiary font-bold uppercase text-[10px] tracking-wider">
                    <th className="py-3 px-4">GPID</th>
                    <th className="py-3 px-4">Idol / Organizer</th>
                    <th className="py-3 px-3">Height</th>
                    <th className="py-3 px-4">Jurisdiction</th>
                    <th className="py-3 px-3">Visarjan Date</th>
                    <th className="py-3 px-4">Final Operational Status</th>
                    <th className="py-3 px-4">Assigned Officer</th>
                    <th className="py-3 px-4 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-subtle">
                  {reports.map((item) => {
                    const isCompleted = item.final_state === 'IMMERSION_COMPLETED';
                    const isHolding = item.final_state === 'SENT_TO_HOLDING' || item.procession_state === 'HOLDING';

                    return (
                      <tr
                        key={item.id}
                        className="hover:bg-elevated-2/50 transition-colors"
                      >
                        {/* GPID */}
                        <td className="py-3 px-4 font-bold mono text-accent whitespace-nowrap">
                          {item.gpid}
                        </td>

                        {/* Name & Association */}
                        <td className="py-3 px-4 max-w-xs">
                          <div className="font-semibold text-text-primary truncate">
                            {item.name || 'Unnamed Idol'}
                          </div>
                          {item.association_name && (
                            <div className="text-[11px] text-text-tertiary truncate">
                              {item.association_name}
                            </div>
                          )}
                        </td>

                        {/* Height badge */}
                        <td className="py-3 px-3 whitespace-nowrap">
                          <span
                            className={`inline-block px-2 py-0.5 rounded text-[11px] font-bold ${
                              item.idol_height >= 26
                                ? 'bg-rose-500/15 text-rose-300 border border-rose-500/30'
                                : item.idol_height >= 21
                                ? 'bg-amber-500/15 text-amber-300 border border-amber-500/30'
                                : 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                            }`}
                          >
                            {item.idol_height ? `${item.idol_height} FT` : '—'}
                          </span>
                        </td>

                        {/* Jurisdiction */}
                        <td className="py-3 px-4 whitespace-nowrap">
                          <div className="font-medium text-text-primary">
                            {item.police_station}
                          </div>
                          <div className="text-[11px] text-text-tertiary">
                            {item.zone} Zone
                          </div>
                        </td>

                        {/* Visarjan Date */}
                        <td className="py-3 px-3 whitespace-nowrap mono text-text-secondary">
                          {item.immersion_date || '—'}
                        </td>

                        {/* Final Operational Status */}
                        <td className="py-3 px-4 whitespace-nowrap">
                          {isCompleted ? (
                            <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 font-semibold text-[11px]">
                              <CheckCircle2 className="w-3.5 h-3.5" />
                              <span>Immersion Completed</span>
                            </span>
                          ) : isHolding ? (
                            <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded bg-amber-500/15 border border-amber-500/30 text-amber-400 font-semibold text-[11px]">
                              <Clock className="w-3.5 h-3.5" />
                              <span>Sent to Holding</span>
                            </span>
                          ) : (
                            <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded bg-elevated-2 border border-border-default text-text-secondary font-medium text-[11px]">
                              <span>{item.final_state_display}</span>
                            </span>
                          )}
                        </td>

                        {/* Assigned Officer */}
                        <td className="py-3 px-4 whitespace-nowrap">
                          {item.assigned_officer ? (
                            <div>
                              <div className="font-medium text-text-primary">
                                {item.assigned_officer.name || item.assigned_officer.username}
                              </div>
                              <div className="text-[10px] text-text-tertiary mono">
                                {item.assigned_officer.username}
                                {item.assigned_officer.police_id
                                  ? ` • ${item.assigned_officer.police_id}`
                                  : ''}
                              </div>
                            </div>
                          ) : (
                            <span className="text-text-tertiary italic">None recorded</span>
                          )}
                        </td>

                        {/* Action: Download PDF Report */}
                        <td className="py-3 px-4 text-right whitespace-nowrap">
                          <a
                            href={getReportDownloadUrl(item.gpid)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-md bg-accent hover:bg-accent-hover text-base font-semibold shadow-sm transition-colors text-xs cursor-pointer"
                            title={`Download official PDF operational report for ${item.gpid}`}
                          >
                            <FileDown className="w-3.5 h-3.5" />
                            <span>Download PDF</span>
                          </a>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Pagination Footer */}
            <div className="px-4 py-3 bg-elevated-1 border-t border-border-subtle flex flex-wrap items-center justify-between gap-3 text-xs text-text-secondary">
              <div>
                Showing{' '}
                <span className="font-bold text-text-primary mono">
                  {(currentPage - 1) * pageSize + 1}
                </span>{' '}
                to{' '}
                <span className="font-bold text-text-primary mono">
                  {Math.min(currentPage * pageSize, totalCount)}
                </span>{' '}
                of <span className="font-bold text-text-primary mono">{totalCount}</span> reports
              </div>

              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage <= 1 || loading}
                  className="px-2.5 py-1 rounded border border-border-default bg-elevated hover:bg-elevated-2 text-text-secondary hover:text-text-primary disabled:opacity-40 disabled:pointer-events-none transition-colors cursor-pointer flex items-center space-x-1"
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                  <span>Previous</span>
                </button>

                <span className="px-2 text-xs font-semibold mono text-text-primary">
                  Page {currentPage} of {totalPages}
                </span>

                <button
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  disabled={currentPage >= totalPages || loading}
                  className="px-2.5 py-1 rounded border border-border-default bg-elevated hover:bg-elevated-2 text-text-secondary hover:text-text-primary disabled:opacity-40 disabled:pointer-events-none transition-colors cursor-pointer flex items-center space-x-1"
                >
                  <span>Next</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
