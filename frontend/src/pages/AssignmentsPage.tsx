import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  Search,
  UserCheck,
  UserX,
  AlertTriangle,
  AlertCircle,
  CheckCircle2,
  X,
  Loader2,
  Download,
  Filter,
  ChevronRight,
  Shield,
  User,
  ChevronLeft,
} from 'lucide-react';
import { useAssignments } from '../hooks/useAssignments';
import {
  fetchAuthoritativePoliceStations,
  fetchAssignableRegistry,
  fetchAssignableIdolDetail,
  fetchEligibleOfficersForGpid,
  assignConstable,
  endAssignment,
  getAssignmentExcelExportUrl,
} from '../api/client';
import {
  AssignableIdol,
  AssignableIdolDetail,
  AssignableSummary,
  EligibleOfficer,
  EligibleOfficersResponse,
  PoliceStationMaster,
  HeightBucketFilter,
  AssignmentStatusFilter,
  VisarjanDateFilter,
} from '../types';
import { LoadingState, EmptyState, ErrorState } from '../components/shared/States';

export const AssignmentsPage: React.FC = () => {
  // Navigation View State
  const [activeTab, setActiveTab] = useState<'console' | 'history'>('console');

  // Filter Bar State
  const [selectedZone, setSelectedZone] = useState<string>('All Zones');
  const [selectedStation, setSelectedStation] = useState<string>('All Police Stations');
  const [selectedHeight, setSelectedHeight] = useState<HeightBucketFilter>('all_15_plus');
  const [selectedStatus, setSelectedStatus] = useState<AssignmentStatusFilter>('all');
  const [visarjanDateMode, setVisarjanDateMode] = useState<VisarjanDateFilter>('all');
  const [customVisarjanDate, setCustomVisarjanDate] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [debouncedSearch, setDebouncedSearch] = useState<string>('');
  const [currentPage, setCurrentPage] = useState<number>(1);

  // Registry Data State
  const [registryData, setRegistryData] = useState<AssignableIdol[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [summary, setSummary] = useState<AssignableSummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Master Reference Data
  const [policeStations, setPoliceStations] = useState<PoliceStationMaster[]>([]);

  // GPID Details Drawer State
  const [drawerGpid, setDrawerGpid] = useState<string | null>(null);
  const [drawerDetail, setDrawerDetail] = useState<AssignableIdolDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState<boolean>(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  // Dedicated Assign Officer Modal State
  const [assignTarget, setAssignTarget] = useState<AssignableIdol | null>(null);
  const [eligibleResponse, setEligibleResponse] = useState<EligibleOfficersResponse | null>(null);
  const [officers, setOfficers] = useState<EligibleOfficer[]>([]);
  const [loadingOfficers, setLoadingOfficers] = useState<boolean>(false);
  const [officersError, setOfficersError] = useState<string | null>(null);
  const [officerFilterQuery, setOfficerFilterQuery] = useState<string>('');
  const [selectedOfficerId, setSelectedOfficerId] = useState<number | null>(null);
  const [assignSubmitting, setAssignSubmitting] = useState<boolean>(false);
  const [assignError, setAssignError] = useState<string | null>(null);

  // End Assignment Modal State
  const [endingAssignment, setEndingAssignment] = useState<{
    id: number;
    idol_gpid: string;
    police_station: string;
    officer_name: string;
    started_at: string;
  } | null>(null);
  const [endReason, setEndReason] = useState<string>('');
  const [endingSubmitting, setEndingSubmitting] = useState<boolean>(false);
  const [endError, setEndError] = useState<string | null>(null);

  // Success Toast
  const [successToast, setSuccessToast] = useState<string | null>(null);

  // Assignment History Hook (for history tab)
  const { assignments: historyAssignments, loading: loadingHistory, error: historyError, reload: reloadHistory } = useAssignments();
  const [historyFilterActive, setHistoryFilterActive] = useState<boolean>(true);

  // Debounce search input
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

  // Compute available zones
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
    return policeStations
      .filter((ps) => ps.zone.toLowerCase() === selectedZone.toLowerCase())
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

  // Primary Data Fetcher for Registry
  const loadRegistry = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchAssignableRegistry({
        page: currentPage,
        page_size: 25,
        zone: selectedZone,
        police_station: selectedStation,
        height_bucket: selectedHeight,
        assignment_status: selectedStatus,
        visarjan_date: computedVisarjanDate,
        search: debouncedSearch.trim() || undefined,
      });
      setRegistryData(data.results || []);
      setTotalCount(data.count || 0);
      setSummary(data.summary || null);
    } catch (err: any) {
      setError(err.message || 'Failed to load eligible GPID registry.');
    } finally {
      setLoading(false);
    }
  }, [currentPage, selectedZone, selectedStation, selectedHeight, selectedStatus, computedVisarjanDate, debouncedSearch]);

  useEffect(() => {
    if (activeTab === 'console') {
      loadRegistry();
    }
  }, [loadRegistry, activeTab]);

  // Load Drawer Details when GPID is clicked
  const handleOpenDrawer = async (gpid: string) => {
    setDrawerGpid(gpid);
    setLoadingDetail(true);
    setDetailError(null);
    try {
      const detail = await fetchAssignableIdolDetail(gpid);
      setDrawerDetail(detail);
    } catch (err: any) {
      setDetailError(err.message || 'Failed to load GPID details.');
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleCloseDrawer = () => {
    setDrawerGpid(null);
    setDrawerDetail(null);
    setDetailError(null);
  };

  // Open Dedicated Assign Modal (authoritative GPID-context endpoint)
  const handleOpenAssignModal = async (idol: AssignableIdol) => {
    setAssignTarget(idol);
    setSelectedOfficerId(null);
    setOfficerFilterQuery('');
    setAssignError(null);
    setLoadingOfficers(true);
    setOfficersError(null);
    setEligibleResponse(null);
    try {
      const data = await fetchEligibleOfficersForGpid(idol.gpid);
      setEligibleResponse(data);
      setOfficers(data.officers || []);
    } catch (err: any) {
      setOfficersError(err.message || 'Failed to load eligible ground staff.');
    } finally {
      setLoadingOfficers(false);
    }
  };

  const handleCloseAssignModal = () => {
    if (assignSubmitting) return;
    setAssignTarget(null);
    setSelectedOfficerId(null);
    setOfficerFilterQuery('');
    setAssignError(null);
    setEligibleResponse(null);
  };

  // Confirm Assignment
  const handleConfirmAssignment = async () => {
    if (!assignTarget || !selectedOfficerId) return;
    setAssignSubmitting(true);
    setAssignError(null);
    try {
      await assignConstable(assignTarget.gpid, selectedOfficerId);
      setSuccessToast(`Officer assigned successfully to ${assignTarget.gpid}.`);
      setTimeout(() => setSuccessToast(null), 4000);
      handleCloseAssignModal();

      // Refresh registry and drawer without full page reload
      await loadRegistry();
      if (drawerGpid === assignTarget.gpid) {
        handleOpenDrawer(assignTarget.gpid);
      }
    } catch (err: any) {
      setAssignError(err.message || 'Failed to complete assignment.');
    } finally {
      setAssignSubmitting(false);
    }
  };

  // Open End Assignment Modal
  const handleOpenEndModal = (item: {
    id: number;
    idol_gpid: string;
    police_station: string;
    officer_name: string;
    started_at: string;
  }) => {
    setEndingAssignment(item);
    setEndReason('');
    setEndError(null);
  };

  const handleCloseEndModal = () => {
    if (endingSubmitting) return;
    setEndingAssignment(null);
    setEndReason('');
    setEndError(null);
  };

  // Confirm End Assignment
  const handleConfirmEndAssignment = async () => {
    if (!endingAssignment) return;
    setEndingSubmitting(true);
    setEndError(null);
    try {
      await endAssignment(endingAssignment.id, endReason.trim());
      setSuccessToast(`Assignment for ${endingAssignment.idol_gpid} ended successfully.`);
      setTimeout(() => setSuccessToast(null), 4000);
      handleCloseEndModal();

      // Refresh registry, drawer, and history
      await loadRegistry();
      if (drawerGpid === endingAssignment.idol_gpid) {
        handleOpenDrawer(endingAssignment.idol_gpid);
      }
      reloadHistory();
    } catch (err: any) {
      setEndError(err.message || 'Failed to end assignment.');
    } finally {
      setEndingSubmitting(false);
    }
  };

  // Filter officers inside Assign Modal
  const filteredModalOfficers = useMemo(() => {
    const q = officerFilterQuery.toLowerCase().trim();
    if (!q) return officers;
    return officers.filter(
      (o) =>
        (o.name && o.name.toLowerCase().includes(q)) ||
        (o.first_name && o.first_name.toLowerCase().includes(q)) ||
        (o.last_name && o.last_name.toLowerCase().includes(q)) ||
        o.username.toLowerCase().includes(q) ||
        (o.police_id && o.police_id.toLowerCase().includes(q))
    );
  }, [officers, officerFilterQuery]);

  // Excel Export Handler
  const handleExportExcel = () => {
    const url = getAssignmentExcelExportUrl({
      zone: selectedZone,
      police_station: selectedStation,
      height_bucket: selectedHeight,
      assignment_status: selectedStatus,
      visarjan_date: computedVisarjanDate,
      search: debouncedSearch.trim() || undefined,
    });
    window.open(url, '_blank');
  };

  // Reset Filters
  const handleResetFilters = () => {
    setSelectedZone('All Zones');
    setSelectedStation('All Police Stations');
    setSelectedHeight('all_15_plus');
    setSelectedStatus('all');
    setVisarjanDateMode('all');
    setCustomVisarjanDate('');
    setSearchQuery('');
    setCurrentPage(1);
  };

  const isFiltered =
    selectedZone !== 'All Zones' ||
    selectedStation !== 'All Police Stations' ||
    selectedHeight !== 'all_15_plus' ||
    selectedStatus !== 'all' ||
    visarjanDateMode !== 'all' ||
    Boolean(searchQuery.trim());

  // Height Badge Visual Styling
  const getHeightBadge = (bucket: string, height: number) => {
    if (bucket === '26+' || height >= 26) {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-rose-500/15 text-rose-400 border border-rose-500/30 mono">
          {height} FT &bull; 26 FT+
        </span>
      );
    }
    if (bucket === '21-25' || (height >= 21 && height < 26)) {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/30 mono">
          {height} FT &bull; 21–25 FT
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 mono">
        {height} FT &bull; 15–20 FT
      </span>
    );
  };

  return (
    <div className="h-full flex flex-col overflow-hidden bg-base relative">
      {/* Toast Notification */}
      {successToast && (
        <div className="fixed top-5 right-6 z-50 flex items-center gap-2 px-4 py-2.5 bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 text-xs font-medium rounded-lg shadow-2xl animate-fade-in-up">
          <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
          <span>{successToast}</span>
        </div>
      )}

      {/* Main Header */}
      <div className="px-6 pt-5 pb-3 border-b border-border-subtle bg-elevated-1 shrink-0 flex items-center justify-between">
        <div>
          <div className="flex items-center space-x-2.5">
            <Shield className="w-5 h-5 text-accent" />
            <h1 className="text-base font-bold text-text-primary tracking-wide uppercase">
              Officer Assignment
            </h1>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-accent/15 text-accent border border-accent/30 tracking-wider">
              15 FT+ MANDATORY
            </span>
          </div>
          <p className="text-xs text-text-tertiary mt-1">
            Assign eligible ground staff to registered Ganesh idols 15 FT and above.
          </p>
        </div>

        {/* View Switcher Tabs & Excel Export Button */}
        <div className="flex items-center space-x-3">
          <button
            onClick={handleExportExcel}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded bg-emerald-600/15 hover:bg-emerald-600/25 border border-emerald-500/30 text-emerald-400 text-xs font-semibold transition-colors cursor-pointer"
            title="Download authoritative officer assignment registry in Microsoft Excel format"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download Excel</span>
          </button>

          <div className="flex items-center bg-elevated p-1 rounded-md border border-border-default text-xs">
            <button
              onClick={() => setActiveTab('console')}
              className={`px-3 py-1 rounded transition-colors cursor-pointer ${
                activeTab === 'console'
                  ? 'bg-accent text-base font-semibold shadow-sm'
                  : 'text-text-secondary hover:text-text-primary'
              }`}
            >
              Assignment Console
            </button>
            <button
              onClick={() => setActiveTab('history')}
              className={`px-3 py-1 rounded transition-colors cursor-pointer ${
                activeTab === 'history'
                  ? 'bg-accent text-base font-semibold shadow-sm'
                  : 'text-text-secondary hover:text-text-primary'
              }`}
            >
              Assignment History
            </button>
          </div>
        </div>
      </div>

      {activeTab === 'console' ? (
        <div className="flex-1 flex flex-col overflow-hidden">
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
                  <option value="all_15_plus">
                    All 15+ FT ({summary ? summary.total_eligible : '…'})
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

              {/* Assignment Status Filter */}
              <div>
                <label className="block text-[10px] uppercase font-bold text-text-tertiary mb-1">
                  Assignment Status
                </label>
                <select
                  value={selectedStatus}
                  onChange={(e) => {
                    setSelectedStatus(e.target.value as AssignmentStatusFilter);
                    setCurrentPage(1);
                  }}
                  className="w-full px-2.5 py-1.5 bg-elevated border border-border-default rounded text-xs text-text-primary focus:outline-none focus:border-accent"
                >
                  <option value="all">All</option>
                  <option value="unassigned">
                    Unassigned ({summary ? summary.unassigned : '…'})
                  </option>
                  <option value="assigned">
                    Assigned ({summary ? summary.assigned : '…'})
                  </option>
                </select>
              </div>

              {/* Search input & clear button */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="block text-[10px] uppercase font-bold text-text-tertiary">
                    Search GPID / Pandal
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
                    placeholder="Search GPID or pandal name…"
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
                  TOTAL ELIGIBLE
                </div>
                <div className="text-xl font-bold text-text-primary mt-0.5 mono">
                  {summary ? summary.total_eligible : '—'}
                </div>
                <div className="text-[10px] text-accent font-medium mt-0.5">15 FT and above</div>
              </div>

              {/* 15-20 FT */}
              <div className="p-3 bg-emerald-950/20 rounded border border-emerald-500/25 shadow-sm">
                <div className="text-[10px] font-bold uppercase tracking-wider text-emerald-400">
                  15–20 FT
                </div>
                <div className="text-xl font-bold text-emerald-300 mt-0.5 mono">
                  {summary ? summary.count_15_20 : '—'}
                </div>
                <div className="text-[10px] text-text-tertiary mt-0.5">Green Category</div>
              </div>

              {/* 21-25 FT */}
              <div className="p-3 bg-amber-950/20 rounded border border-amber-500/25 shadow-sm">
                <div className="text-[10px] font-bold uppercase tracking-wider text-amber-400">
                  21–25 FT
                </div>
                <div className="text-xl font-bold text-amber-300 mt-0.5 mono">
                  {summary ? summary.count_21_25 : '—'}
                </div>
                <div className="text-[10px] text-text-tertiary mt-0.5">Yellow Category</div>
              </div>

              {/* 26 FT+ */}
              <div className="p-3 bg-rose-950/20 rounded border border-rose-500/25 shadow-sm">
                <div className="text-[10px] font-bold uppercase tracking-wider text-rose-400">
                  26 FT+
                </div>
                <div className="text-xl font-bold text-rose-300 mt-0.5 mono">
                  {summary ? summary.count_26_plus : '—'}
                </div>
                <div className="text-[10px] text-text-tertiary mt-0.5">Red Category</div>
              </div>

              {/* Assigned */}
              <div className="p-3 bg-elevated rounded border border-border-default shadow-sm">
                <div className="text-[10px] font-bold uppercase tracking-wider text-emerald-400">
                  ASSIGNED
                </div>
                <div className="text-xl font-bold text-emerald-400 mt-0.5 mono">
                  {summary ? summary.assigned : '—'}
                </div>
                <div className="text-[10px] text-text-tertiary mt-0.5">Active Ground Staff</div>
              </div>

              {/* Unassigned */}
              <div className="p-3 bg-elevated rounded border border-border-default shadow-sm">
                <div className="text-[10px] font-bold uppercase tracking-wider text-text-tertiary">
                  UNASSIGNED
                </div>
                <div className="text-xl font-bold text-text-primary mt-0.5 mono">
                  {summary ? summary.unassigned : '—'}
                </div>
                <div className="text-[10px] text-accent font-medium mt-0.5">Pending Assignment</div>
              </div>
            </div>
          </div>

          {/* Table Container */}
          <div className="flex-1 overflow-y-auto px-6 py-4">
            {loading && <LoadingState label="Loading eligible GPID registry…" />}
            {!loading && error && <ErrorState message={error} onRetry={loadRegistry} />}
            {!loading && !error && registryData.length === 0 && (
              <div className="py-12 text-center bg-elevated rounded-lg border border-border-subtle p-6 space-y-2">
                <Filter className="w-8 h-8 mx-auto text-text-tertiary" />
                <h3 className="text-sm font-semibold text-text-primary">No eligible GPIDs found</h3>
                <p className="text-xs text-text-tertiary max-w-md mx-auto">
                  No idols (≥15 FT) match the current filter criteria:
                  {selectedZone !== 'All Zones' && ` Zone: ${selectedZone};`}
                  {selectedStation !== 'All Police Stations' && ` Police Station: ${selectedStation};`}
                  {selectedHeight !== 'all_15_plus' && ` Height: ${selectedHeight};`}
                  {selectedStatus !== 'all' && ` Status: ${selectedStatus};`}
                  {debouncedSearch && ` Search: "${debouncedSearch}".`}
                </p>
                <button
                  onClick={handleResetFilters}
                  className="mt-3 px-3.5 py-1.5 text-xs rounded bg-accent text-base font-semibold hover:opacity-90 transition-opacity cursor-pointer"
                >
                  Clear All Filters
                </button>
              </div>
            )}

            {!loading && !error && registryData.length > 0 && (
              <div className="bg-elevated border border-border-default rounded-lg shadow-sm overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="bg-base border-b border-border-subtle text-[10px] font-bold uppercase tracking-wider text-text-tertiary">
                        <th className="px-4 py-3">GPID</th>
                        <th className="px-4 py-3">Pandal / Idol Name</th>
                        <th className="px-4 py-3">Height</th>
                        <th className="px-4 py-3">Visarjan Date</th>
                        <th className="px-4 py-3">Zone</th>
                        <th className="px-4 py-3">Police Station</th>
                        <th className="px-4 py-3">Assignment</th>
                        <th className="px-4 py-3">Procession</th>
                        <th className="px-4 py-3 text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border-subtle">
                      {registryData.map((idol) => {
                        const isAssigned = Boolean(idol.assignment);
                        return (
                          <tr
                            key={idol.id}
                            className="hover:bg-elevated-2/60 transition-colors group"
                          >
                            {/* GPID */}
                            <td className="px-4 py-3">
                              <button
                                onClick={() => handleOpenDrawer(idol.gpid)}
                                className="mono font-bold text-accent hover:underline flex items-center space-x-1 cursor-pointer"
                                title="Click to view full operational details & timeline"
                              >
                                <span>{idol.gpid}</span>
                                <ChevronRight className="w-3 h-3 text-text-tertiary group-hover:translate-x-0.5 transition-transform" />
                              </button>
                            </td>

                            {/* Pandal / Idol Name */}
                            <td className="px-4 py-3">
                              <div className="font-semibold text-text-primary truncate max-w-[200px]">
                                {idol.name || idol.association_name || 'Ganesh Idol'}
                              </div>
                              {idol.association_name && idol.name && (
                                <div className="text-[11px] text-text-tertiary truncate max-w-[200px]">
                                  {idol.association_name}
                                </div>
                              )}
                            </td>

                            {/* Height Badge */}
                            <td className="px-4 py-3">
                              {getHeightBadge(idol.height_bucket, idol.idol_height)}
                            </td>

                            {/* Visarjan Date */}
                            <td className="px-4 py-3 text-text-secondary mono text-[11px] whitespace-nowrap">
                              {idol.visarjan_date || idol.immersion_date || '—'}
                            </td>

                            {/* Zone */}
                            <td className="px-4 py-3 text-text-secondary truncate max-w-[120px]">
                              {idol.zone}
                            </td>

                            {/* Police Station */}
                            <td className="px-4 py-3 text-text-secondary font-medium truncate max-w-[130px]">
                              {idol.police_station}
                            </td>

                            {/* Assignment Status */}
                            <td className="px-4 py-3">
                              {isAssigned ? (
                                <div className="space-y-0.5">
                                  <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                                    ASSIGNED
                                  </span>
                                  <div className="font-medium text-text-primary text-[11px] truncate max-w-[150px]">
                                    {idol.assignment?.officer_name}
                                  </div>
                                  {idol.assignment?.police_id && (
                                    <div className="text-[10px] text-text-tertiary mono">
                                      ID: {idol.assignment.police_id}
                                    </div>
                                  )}
                                </div>
                              ) : (
                                <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-stone-500/15 text-text-tertiary border border-stone-500/30">
                                  UNASSIGNED
                                </span>
                              )}
                            </td>

                            {/* Procession Status */}
                            <td className="px-4 py-3">
                              <span className="text-[11px] font-medium text-text-secondary">
                                {idol.procession_state.replace('_', ' ')}
                              </span>
                            </td>

                            {/* Actions */}
                            <td className="px-4 py-3 text-right">
                              {isAssigned ? (
                                <div className="flex items-center justify-end space-x-1.5">
                                  <button
                                    onClick={() => handleOpenDrawer(idol.gpid)}
                                    className="px-2.5 py-1 text-[11px] font-medium rounded border border-border-default bg-elevated hover:bg-elevated-2 text-text-secondary hover:text-text-primary transition-colors cursor-pointer"
                                  >
                                    View
                                  </button>
                                  <button
                                    onClick={() =>
                                      handleOpenEndModal({
                                        id: idol.assignment!.id,
                                        idol_gpid: idol.gpid,
                                        police_station: idol.police_station,
                                        officer_name: idol.assignment!.officer_name,
                                        started_at: idol.assignment!.started_at,
                                      })
                                    }
                                    className="px-2 py-1 text-[11px] font-medium rounded border border-rose-500/30 bg-rose-500/10 text-rose-400 hover:bg-rose-500/20 transition-colors cursor-pointer"
                                    title="End this active officer assignment"
                                  >
                                    End
                                  </button>
                                </div>
                              ) : (
                                <button
                                  onClick={() => handleOpenAssignModal(idol)}
                                  className="px-3 py-1.5 text-xs font-semibold rounded bg-accent hover:opacity-90 text-base transition-opacity cursor-pointer shadow-sm flex items-center space-x-1 ml-auto"
                                >
                                  <UserCheck className="w-3.5 h-3.5" />
                                  <span>Assign Officer</span>
                                </button>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                {/* Pagination Controls */}
                <div className="px-4 py-3 bg-base border-t border-border-subtle flex items-center justify-between text-xs text-text-tertiary">
                  <div>
                    Showing{' '}
                    <span className="font-semibold text-text-primary mono">
                      {Math.min(1 + (currentPage - 1) * 25, totalCount)}
                    </span>{' '}
                    to{' '}
                    <span className="font-semibold text-text-primary mono">
                      {Math.min(currentPage * 25, totalCount)}
                    </span>{' '}
                    of{' '}
                    <span className="font-semibold text-text-primary mono">
                      {totalCount}
                    </span>{' '}
                    eligible records
                  </div>
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                      disabled={currentPage <= 1}
                      className="px-2.5 py-1 rounded border border-border-default disabled:opacity-30 hover:bg-elevated text-text-primary transition-colors cursor-pointer flex items-center space-x-1"
                    >
                      <ChevronLeft className="w-3.5 h-3.5" />
                      <span>Prev</span>
                    </button>
                    <span className="mono font-semibold text-text-secondary">
                      Page {currentPage} of {Math.max(1, Math.ceil(totalCount / 25))}
                    </span>
                    <button
                      onClick={() => setCurrentPage((p) => p + 1)}
                      disabled={currentPage >= Math.ceil(totalCount / 25)}
                      className="px-2.5 py-1 rounded border border-border-default disabled:opacity-30 hover:bg-elevated text-text-primary transition-colors cursor-pointer flex items-center space-x-1"
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
      ) : (
        /* History View Tab */
        <div className="flex-1 flex flex-col overflow-hidden px-6 py-4">
          <div className="flex items-center justify-between pb-3">
            <h2 className="text-xs font-bold uppercase tracking-wider text-text-secondary">
              Historical & Completed Assignment Records
            </h2>
            <div className="flex items-center space-x-1 bg-elevated p-1 rounded border border-border-default text-xs">
              <button
                onClick={() => setHistoryFilterActive(true)}
                className={`px-3 py-1 rounded transition-colors cursor-pointer ${
                  historyFilterActive
                    ? 'bg-accent text-base font-semibold'
                    : 'text-text-secondary hover:text-text-primary'
                }`}
              >
                Active Only
              </button>
              <button
                onClick={() => setHistoryFilterActive(false)}
                className={`px-3 py-1 rounded transition-colors cursor-pointer ${
                  !historyFilterActive
                    ? 'bg-accent text-base font-semibold'
                    : 'text-text-secondary hover:text-text-primary'
                }`}
              >
                All History
              </button>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto">
            {loadingHistory && <LoadingState label="Loading assignment history…" />}
            {!loadingHistory && historyError && (
              <ErrorState message={historyError} onRetry={reloadHistory} />
            )}
            {!loadingHistory &&
              !historyError &&
              historyAssignments.filter((a) => (!historyFilterActive ? true : a.is_active)).length ===
                0 && (
                <EmptyState
                  title={
                    historyFilterActive
                      ? 'No active assignments found'
                      : 'No historical records available'
                  }
                />
              )}

            {!loadingHistory &&
              !historyError &&
              historyAssignments.filter((a) => (!historyFilterActive ? true : a.is_active)).length >
                0 && (
                <div className="bg-elevated border border-border-default rounded-lg overflow-hidden shadow-sm">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="bg-base border-b border-border-subtle text-[10px] font-bold uppercase tracking-wider text-text-tertiary">
                        <th className="px-4 py-3">GPID</th>
                        <th className="px-4 py-3">Station</th>
                        <th className="px-4 py-3">Constable</th>
                        <th className="px-4 py-3">Started</th>
                        <th className="px-4 py-3">Ended</th>
                        <th className="px-4 py-3">Status</th>
                        <th className="px-4 py-3 text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border-subtle">
                      {historyAssignments
                        .filter((a) => (!historyFilterActive ? true : a.is_active))
                        .map((a) => (
                          <tr key={a.id} className="hover:bg-elevated-2/50 transition-colors">
                            <td className="px-4 py-2.5 mono font-semibold text-accent">
                              {a.idol_gpid}
                            </td>
                            <td className="px-4 py-2.5 text-text-secondary">{a.police_station}</td>
                            <td className="px-4 py-2.5 font-medium text-text-primary">
                              {a.constable_name || a.constable_username}
                              {a.constable_police_id && (
                                <span className="text-[10px] text-text-tertiary mono ml-1">
                                  ({a.constable_police_id})
                                </span>
                              )}
                            </td>
                            <td className="px-4 py-2.5 text-text-tertiary mono">
                              {new Date(a.started_at).toLocaleString([], {
                                dateStyle: 'short',
                                timeStyle: 'short',
                              })}
                            </td>
                            <td className="px-4 py-2.5 text-text-tertiary mono">
                              {a.ended_at
                                ? new Date(a.ended_at).toLocaleString([], {
                                    dateStyle: 'short',
                                    timeStyle: 'short',
                                  })
                                : '—'}
                            </td>
                            <td className="px-4 py-2.5">
                              <span
                                className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${
                                  a.is_active
                                    ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                                    : 'bg-stone-500/15 text-text-tertiary border border-stone-500/30'
                                }`}
                              >
                                {a.is_active ? 'ACTIVE' : 'ENDED'}
                              </span>
                            </td>
                            <td className="px-4 py-2.5 text-right">
                              {a.is_active && (
                                <button
                                  onClick={() =>
                                    handleOpenEndModal({
                                      id: a.id,
                                      idol_gpid: a.idol_gpid,
                                      police_station: a.police_station,
                                      officer_name: a.constable_name || a.constable_username,
                                      started_at: a.started_at,
                                    })
                                  }
                                  className="px-2 py-1 text-[11px] font-medium rounded border border-rose-500/30 bg-rose-500/10 text-rose-400 hover:bg-rose-500/20 transition-colors cursor-pointer"
                                >
                                  End
                                </button>
                              )}
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              )}
          </div>
        </div>
      )}

      {/* GPID Details Drawer */}
      {drawerGpid && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/70 backdrop-blur-xs animate-fade-in">
          <div className="w-full max-w-lg bg-base border-l border-border-default shadow-2xl flex flex-col h-full overflow-hidden animate-slide-left">
            {/* Drawer Header */}
            <div className="p-4 border-b border-border-subtle bg-elevated-1 flex items-center justify-between shrink-0">
              <div>
                <span className="text-[10px] uppercase font-bold tracking-widest text-text-tertiary block">
                  Authoritative GPID Details
                </span>
                <span className="text-base font-bold text-accent mono">{drawerGpid}</span>
              </div>
              <button
                onClick={handleCloseDrawer}
                className="p-1 rounded text-text-tertiary hover:text-text-primary hover:bg-elevated transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Drawer Content */}
            <div className="flex-1 overflow-y-auto p-5 space-y-4 text-xs">
              {loadingDetail && <LoadingState label="Loading detailed operational record…" />}
              {!loadingDetail && detailError && <ErrorState message={detailError} />}

              {!loadingDetail && !detailError && drawerDetail && (
                <>
                  {/* Status & Freshness Ribbon */}
                  <div className="p-3 bg-elevated rounded-lg border border-border-default flex items-center justify-between">
                    <div>
                      <span className="text-[10px] uppercase font-bold text-text-tertiary block">
                        Procession Status
                      </span>
                      <span className="font-bold text-text-primary">
                        {drawerDetail.procession_state.replace('_', ' ')}
                      </span>
                    </div>
                    <div className="text-right">
                      <span className="text-[10px] uppercase font-bold text-text-tertiary block">
                        Live Telemetry
                      </span>
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                          drawerDetail.connection_state === 'LIVE'
                            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                            : drawerDetail.connection_state === 'DEGRADED'
                            ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40'
                            : 'bg-stone-500/20 text-text-tertiary border border-stone-500/40'
                        }`}
                      >
                        {drawerDetail.connection_state}
                      </span>
                    </div>
                  </div>

                  {/* Operational Summary Grid */}
                  <div className="p-4 bg-elevated-1 rounded-lg border border-border-default space-y-3">
                    <div className="flex items-center justify-between pb-2 border-b border-border-subtle">
                      <span className="text-xs font-bold uppercase text-accent tracking-wider">
                        Idol Specifications
                      </span>
                      {getHeightBadge(drawerDetail.height_bucket, drawerDetail.idol_height)}
                    </div>

                    <div className="grid grid-cols-2 gap-3 text-[11px]">
                      <div>
                        <span className="text-text-tertiary uppercase text-[10px] block font-bold">
                          Organizer / Mandap
                        </span>
                        <span className="font-semibold text-text-primary">
                          {drawerDetail.name || 'Ganesh Utsav Pandal'}
                        </span>
                      </div>
                      <div>
                        <span className="text-text-tertiary uppercase text-[10px] block font-bold">
                          Association
                        </span>
                        <span className="text-text-secondary">
                          {drawerDetail.association_name || '—'}
                        </span>
                      </div>
                      <div>
                        <span className="text-text-tertiary uppercase text-[10px] block font-bold">
                          Zone
                        </span>
                        <span className="font-medium text-text-primary">{drawerDetail.zone}</span>
                      </div>
                      <div>
                        <span className="text-text-tertiary uppercase text-[10px] block font-bold">
                          Police Station
                        </span>
                        <span className="font-medium text-text-primary">
                          {drawerDetail.police_station}
                        </span>
                      </div>
                      <div className="col-span-2">
                        <span className="text-text-tertiary uppercase text-[10px] block font-bold">
                          Authoritative Visarjan Date
                        </span>
                        <span className="font-semibold text-accent mono">
                          {drawerDetail.visarjan_date || drawerDetail.immersion_date || '—'}
                        </span>
                      </div>
                      <div className="col-span-2">
                        <span className="text-text-tertiary uppercase text-[10px] block font-bold">
                          Origin Address
                        </span>
                        <span className="text-text-secondary">{drawerDetail.address}</span>
                      </div>
                      <div className="col-span-2">
                        <span className="text-text-tertiary uppercase text-[10px] block font-bold">
                          Destination Waterbody
                        </span>
                        <span className="text-text-secondary font-medium">
                          {drawerDetail.destination}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Active Officer Assignment Card */}
                  <div className="p-4 bg-elevated-1 rounded-lg border border-border-default space-y-2">
                    <span className="text-xs font-bold uppercase text-accent tracking-wider block">
                      Ground Staff Assignment
                    </span>
                    {drawerDetail.assignment ? (
                      <div className="p-3 bg-elevated rounded border border-border-subtle space-y-2">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-2">
                            <UserCheck className="w-4 h-4 text-emerald-400" />
                            <span className="font-bold text-text-primary text-xs">
                              {drawerDetail.assignment.officer_name}
                            </span>
                          </div>
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                            ON DUTY
                          </span>
                        </div>
                        <div className="grid grid-cols-2 gap-2 text-[11px] text-text-tertiary">
                          <div>
                            Badge ID:{' '}
                            <span className="mono text-text-secondary font-medium">
                              {drawerDetail.assignment.police_id || '—'}
                            </span>
                          </div>
                          <div>
                            Station:{' '}
                            <span className="text-text-secondary font-medium">
                              {drawerDetail.assignment.police_station || drawerDetail.police_station}
                            </span>
                          </div>
                          {drawerDetail.assignment.started_at && (
                            <div className="col-span-2">
                              Assigned At:{' '}
                              <span className="mono text-text-secondary">
                                {new Date(drawerDetail.assignment.started_at).toLocaleString([], {
                                  dateStyle: 'short',
                                  timeStyle: 'medium',
                                })}
                              </span>
                            </div>
                          )}
                        </div>
                      </div>
                    ) : (
                      <div className="p-3 bg-elevated rounded border border-border-subtle text-text-tertiary text-center space-y-2">
                        <p>No ground officer is currently assigned to this idol.</p>
                        <button
                          onClick={() => {
                            const idolItem = registryData.find((r) => r.gpid === drawerGpid);
                            if (idolItem) handleOpenAssignModal(idolItem);
                          }}
                          className="px-3 py-1.5 rounded bg-accent text-base font-semibold hover:opacity-90 transition-opacity cursor-pointer inline-flex items-center space-x-1 text-xs"
                        >
                          <UserCheck className="w-3.5 h-3.5" />
                          <span>Assign Ground Constable</span>
                        </button>
                      </div>
                    )}
                  </div>

                  {/* Procession Lifecycle Timeline */}
                  <div className="p-4 bg-elevated-1 rounded-lg border border-border-default space-y-3">
                    <span className="text-xs font-bold uppercase text-accent tracking-wider block">
                      Procession Timeline
                    </span>

                    <div className="space-y-3 pl-2 relative border-l border-border-default ml-2">
                      {/* 1. Assigned */}
                      <div className="relative pl-4">
                        <span
                          className={`w-2.5 h-2.5 rounded-full absolute -left-[5px] top-1 ${
                            drawerDetail.milestones.assigned
                              ? 'bg-emerald-400 ring-4 ring-emerald-500/20'
                              : 'bg-stone-600'
                          }`}
                        />
                        <div className="flex items-center justify-between">
                          <span
                            className={`font-semibold ${
                              drawerDetail.milestones.assigned
                                ? 'text-text-primary'
                                : 'text-text-tertiary'
                            }`}
                          >
                            Assigned
                          </span>
                          <span className="mono text-[10px] text-text-tertiary">
                            {drawerDetail.milestones.assigned
                              ? new Date(drawerDetail.milestones.assigned).toLocaleTimeString()
                              : 'Pending'}
                          </span>
                        </div>
                      </div>

                      {/* 2. Reached Site */}
                      <div className="relative pl-4">
                        <span
                          className={`w-2.5 h-2.5 rounded-full absolute -left-[5px] top-1 ${
                            drawerDetail.milestones.reached_site
                              ? 'bg-emerald-400 ring-4 ring-emerald-500/20'
                              : 'bg-stone-600'
                          }`}
                        />
                        <div className="flex items-center justify-between">
                          <span
                            className={`font-semibold ${
                              drawerDetail.milestones.reached_site
                                ? 'text-text-primary'
                                : 'text-text-tertiary'
                            }`}
                          >
                            Reached Site
                          </span>
                          <span className="mono text-[10px] text-text-tertiary">
                            {drawerDetail.milestones.reached_site
                              ? new Date(drawerDetail.milestones.reached_site).toLocaleTimeString()
                              : 'Pending'}
                          </span>
                        </div>
                      </div>

                      {/* 3. Procession Started */}
                      <div className="relative pl-4">
                        <span
                          className={`w-2.5 h-2.5 rounded-full absolute -left-[5px] top-1 ${
                            drawerDetail.milestones.procession_started
                              ? 'bg-emerald-400 ring-4 ring-emerald-500/20'
                              : 'bg-stone-600'
                          }`}
                        />
                        <div className="flex items-center justify-between">
                          <span
                            className={`font-semibold ${
                              drawerDetail.milestones.procession_started
                                ? 'text-text-primary'
                                : 'text-text-tertiary'
                            }`}
                          >
                            Procession Started
                          </span>
                          <span className="mono text-[10px] text-text-tertiary">
                            {drawerDetail.milestones.procession_started
                              ? new Date(drawerDetail.milestones.procession_started).toLocaleTimeString()
                              : 'Pending'}
                          </span>
                        </div>
                      </div>

                      {/* 4. Reached Visarjan Site */}
                      <div className="relative pl-4">
                        <span
                          className={`w-2.5 h-2.5 rounded-full absolute -left-[5px] top-1 ${
                            drawerDetail.milestones.reached_visarjan
                              ? 'bg-emerald-400 ring-4 ring-emerald-500/20'
                              : 'bg-stone-600'
                          }`}
                        />
                        <div className="flex items-center justify-between">
                          <span
                            className={`font-semibold ${
                              drawerDetail.milestones.reached_visarjan
                                ? 'text-text-primary'
                                : 'text-text-tertiary'
                            }`}
                          >
                            Reached Visarjan Site
                          </span>
                          <span className="mono text-[10px] text-text-tertiary">
                            {drawerDetail.milestones.reached_visarjan
                              ? new Date(drawerDetail.milestones.reached_visarjan).toLocaleTimeString()
                              : 'Pending'}
                          </span>
                        </div>
                      </div>

                      {/* 5. Visarjan Completed */}
                      <div className="relative pl-4">
                        <span
                          className={`w-2.5 h-2.5 rounded-full absolute -left-[5px] top-1 ${
                            drawerDetail.milestones.visarjan_completed
                              ? 'bg-emerald-400 ring-4 ring-emerald-500/20'
                              : 'bg-stone-600'
                          }`}
                        />
                        <div className="flex items-center justify-between">
                          <span
                            className={`font-semibold ${
                              drawerDetail.milestones.visarjan_completed
                                ? 'text-text-primary'
                                : 'text-text-tertiary'
                            }`}
                          >
                            Visarjan Completed
                          </span>
                          <span className="mono text-[10px] text-text-tertiary">
                            {drawerDetail.milestones.visarjan_completed
                              ? new Date(drawerDetail.milestones.visarjan_completed).toLocaleTimeString()
                              : 'Pending'}
                          </span>
                        </div>
                      </div>

                      {/* 6. Returned to Origin */}
                      <div className="relative pl-4">
                        <span
                          className={`w-2.5 h-2.5 rounded-full absolute -left-[5px] top-1 ${
                            drawerDetail.milestones.returned_to_origin
                              ? 'bg-emerald-400 ring-4 ring-emerald-500/20'
                              : 'bg-stone-600'
                          }`}
                        />
                        <div className="flex items-center justify-between">
                          <span
                            className={`font-semibold ${
                              drawerDetail.milestones.returned_to_origin
                                ? 'text-text-primary'
                                : 'text-text-tertiary'
                            }`}
                          >
                            Returned to Origin
                          </span>
                          <span className="mono text-[10px] text-text-tertiary">
                            {drawerDetail.milestones.returned_to_origin
                              ? new Date(drawerDetail.milestones.returned_to_origin).toLocaleTimeString()
                              : 'Pending'}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>

            {/* Drawer Footer Actions */}
            {drawerDetail && (
              <div className="p-4 border-t border-border-subtle bg-elevated-1 shrink-0 flex items-center justify-between">
                {drawerDetail.assignment ? (
                  <button
                    onClick={() =>
                      handleOpenEndModal({
                        id: drawerDetail.assignment!.id,
                        idol_gpid: drawerDetail.gpid,
                        police_station: drawerDetail.police_station,
                        officer_name: drawerDetail.assignment!.officer_name,
                        started_at: drawerDetail.assignment!.started_at,
                      })
                    }
                    className="w-full py-2 rounded bg-rose-600 hover:bg-rose-500 text-white font-semibold transition-colors cursor-pointer text-xs flex items-center justify-center space-x-1.5"
                  >
                    <UserX className="w-3.5 h-3.5" />
                    <span>End Active Assignment</span>
                  </button>
                ) : (
                  <button
                    onClick={() => {
                      const idolItem = registryData.find((r) => r.gpid === drawerGpid);
                      if (idolItem) handleOpenAssignModal(idolItem);
                    }}
                    className="w-full py-2 rounded bg-accent hover:opacity-90 text-base font-semibold transition-opacity cursor-pointer text-xs flex items-center justify-center space-x-1.5"
                  >
                    <UserCheck className="w-3.5 h-3.5" />
                    <span>Assign Officer to GPID</span>
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Dedicated Assign Officer Modal */}
      {assignTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg bg-elevated border border-border-default rounded-lg shadow-2xl overflow-hidden flex flex-col max-h-[90vh] animate-fade-in-up">
            {/* Modal Header */}
            <div className="px-5 py-3.5 bg-base border-b border-border-subtle flex items-center justify-between shrink-0">
              <div className="flex items-center space-x-2">
                <UserCheck className="w-4 h-4 text-accent" />
                <h2 className="text-sm font-bold text-text-primary uppercase tracking-wider">
                  Assign Officer
                </h2>
              </div>
              <button
                onClick={handleCloseAssignModal}
                disabled={assignSubmitting}
                className="text-text-tertiary hover:text-text-primary transition-colors cursor-pointer disabled:opacity-50"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Target Idol Summary */}
            <div className="px-5 py-3 bg-elevated-2 border-b border-border-subtle grid grid-cols-3 gap-2 text-[11px] shrink-0">
              <div>
                <span className="text-text-tertiary uppercase text-[10px] block font-bold">GPID</span>
                <span className="font-bold text-accent mono">{assignTarget.gpid}</span>
              </div>
              <div>
                <span className="text-text-tertiary uppercase text-[10px] block font-bold">Height</span>
                <span className="font-semibold text-text-primary mono">
                  {assignTarget.idol_height} FT
                </span>
              </div>
              <div>
                <span className="text-text-tertiary uppercase text-[10px] block font-bold">Visarjan Date</span>
                <span className="font-semibold text-accent mono">
                  {assignTarget.visarjan_date || assignTarget.immersion_date || '—'}
                </span>
              </div>
              <div>
                <span className="text-text-tertiary uppercase text-[10px] block font-bold">Zone</span>
                <span className="text-text-secondary">{assignTarget.zone}</span>
              </div>
              <div className="col-span-2">
                <span className="text-text-tertiary uppercase text-[10px] block font-bold">
                  Police Station
                </span>
                <span className="font-semibold text-text-primary">
                  {assignTarget.police_station}
                </span>
              </div>
            </div>

            {eligibleResponse?.is_already_assigned && (
              <div className="mx-5 mt-3 p-3 bg-amber-500/15 border border-amber-500/30 rounded text-amber-300 text-xs flex items-start space-x-2 shrink-0">
                <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-amber-400" />
                <span>
                  This idol is currently assigned to <strong>{eligibleResponse.current_assignment?.full_name || eligibleResponse.current_assignment?.username}</strong>. Assigning a new officer will reassign duty.
                </span>
              </div>
            )}

            {/* Officer Selection List */}
            <div className="p-5 space-y-3 flex-1 overflow-y-auto">
              <div className="flex items-center justify-between">
                <label className="block text-xs font-bold uppercase text-text-secondary">
                  Eligible Available Ground Staff
                </label>
                <span className="text-[10px] text-text-tertiary mono">
                  {filteredModalOfficers.length} available in {assignTarget.police_station}
                </span>
              </div>

              {/* Search Officer Input */}
              <div className="relative">
                <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-text-tertiary" />
                <input
                  type="text"
                  value={officerFilterQuery}
                  onChange={(e) => setOfficerFilterQuery(e.target.value)}
                  placeholder="Filter by officer name or police badge ID…"
                  className="w-full pl-8 pr-2.5 py-1.5 bg-base border border-border-default rounded text-xs text-text-primary focus:outline-none focus:border-accent"
                />
              </div>

              {/* Officers Cards List */}
              <div className="border border-border-default rounded-md bg-base max-h-56 overflow-y-auto divide-y divide-border-subtle">
                {loadingOfficers ? (
                  <div className="py-8 flex items-center justify-center space-x-2 text-text-tertiary text-xs">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Loading available officers…</span>
                  </div>
                ) : officersError ? (
                  <div className="p-4 text-rose-400 text-xs flex items-center space-x-2">
                    <AlertCircle className="w-4 h-4 shrink-0" />
                    <span>{officersError}</span>
                  </div>
                ) : filteredModalOfficers.length === 0 ? (
                  <div className="py-8 px-4 text-center text-text-tertiary text-xs space-y-2">
                    <AlertCircle className="w-6 h-6 text-amber-400 mx-auto" />
                    <p className="font-semibold text-text-primary text-sm">No eligible unassigned constables found</p>
                    <p className="text-[11px] leading-relaxed max-w-sm mx-auto">
                      No active, unassigned ground staff (Constables) registered under{' '}
                      <span className="font-semibold text-text-secondary">{assignTarget.police_station}</span> ({assignTarget.zone}).
                    </p>
                    <p className="text-[10px] text-text-tertiary">
                      Use <strong>User Management</strong> to create a new Constable or check inactive accounts for this police station.
                    </p>
                  </div>
                ) : (
                  filteredModalOfficers.map((officer) => {
                    const isSelected = selectedOfficerId === officer.id;
                    const officerDisplayName = officer.name || `${officer.first_name || ''} ${officer.last_name || ''}`.trim() || officer.username;
                    return (
                      <div
                        key={officer.id}
                        onClick={() => setSelectedOfficerId(officer.id)}
                        className={`p-3 flex items-center justify-between cursor-pointer transition-colors ${
                          isSelected
                            ? 'bg-accent/15 border-l-3 border-accent'
                            : 'hover:bg-elevated'
                        }`}
                      >
                        <div className="flex items-center space-x-3 min-w-0">
                          <div
                            className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 ${
                              isSelected
                                ? 'bg-accent text-base font-bold'
                                : 'bg-elevated-2 text-text-secondary'
                            }`}
                          >
                            <User className="w-3.5 h-3.5" />
                          </div>
                          <div className="min-w-0">
                            <div className="font-bold text-text-primary text-xs truncate">
                              {officerDisplayName}
                            </div>
                            <div className="text-[10px] text-text-tertiary mono">
                              Badge ID: {officer.police_id || 'N/A'} &bull; {officer.police_station} &bull; {officer.zone}
                            </div>
                          </div>
                        </div>

                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                          Available
                        </span>
                      </div>
                    );
                  })
                )}
              </div>

              {/* Error Alert */}
              {assignError && (
                <div className="p-3 bg-rose-500/15 border border-rose-500/30 rounded text-rose-300 text-xs flex items-start space-x-2">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                  <span>{assignError}</span>
                </div>
              )}
            </div>

            {/* Modal Actions */}
            <div className="px-5 py-3.5 bg-base border-t border-border-subtle flex items-center justify-end space-x-3 shrink-0">
              <button
                type="button"
                onClick={handleCloseAssignModal}
                disabled={assignSubmitting}
                className="px-4 py-2 rounded border border-border-default text-text-secondary hover:text-text-primary hover:bg-elevated transition-colors cursor-pointer text-xs disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmAssignment}
                disabled={assignSubmitting || !selectedOfficerId}
                className="px-4 py-2 bg-accent hover:opacity-90 disabled:opacity-40 text-base font-bold rounded text-xs transition-opacity cursor-pointer flex items-center space-x-1.5 shadow-sm"
              >
                {assignSubmitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                <span>{assignSubmitting ? 'Assigning…' : 'Confirm Assignment'}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* End Assignment Confirmation Modal */}
      {endingAssignment && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-md bg-elevated border border-border-default rounded-lg shadow-2xl overflow-hidden flex flex-col animate-fade-in-up">
            {/* Modal Header */}
            <div className="px-5 py-3.5 bg-base border-b border-border-subtle flex items-center justify-between shrink-0">
              <div className="flex items-center space-x-2">
                <AlertTriangle className="w-4 h-4 text-rose-400" />
                <h2 className="text-sm font-bold text-text-primary uppercase tracking-wider">
                  End Assignment
                </h2>
              </div>
              <button
                onClick={handleCloseEndModal}
                disabled={endingSubmitting}
                className="text-text-tertiary hover:text-text-primary transition-colors cursor-pointer disabled:opacity-50"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-5 space-y-4 text-xs">
              <div className="p-3.5 bg-elevated-2 border border-border-subtle rounded space-y-2">
                <div className="grid grid-cols-2 gap-2 text-[11px]">
                  <div>
                    <span className="text-text-tertiary block text-[10px] uppercase font-bold">
                      GPID
                    </span>
                    <span className="font-bold text-accent mono">
                      {endingAssignment.idol_gpid}
                    </span>
                  </div>
                  <div>
                    <span className="text-text-tertiary block text-[10px] uppercase font-bold">
                      Police Station
                    </span>
                    <span className="font-semibold text-text-primary">
                      {endingAssignment.police_station}
                    </span>
                  </div>
                  <div>
                    <span className="text-text-tertiary block text-[10px] uppercase font-bold">
                      Assigned Officer
                    </span>
                    <span className="font-bold text-text-primary">
                      {endingAssignment.officer_name}
                    </span>
                  </div>
                  <div>
                    <span className="text-text-tertiary block text-[10px] uppercase font-bold">
                      Started
                    </span>
                    <span className="mono text-text-secondary">
                      {new Date(endingAssignment.started_at).toLocaleString([], {
                        dateStyle: 'short',
                        timeStyle: 'short',
                      })}
                    </span>
                  </div>
                </div>
              </div>

              {/* Warning Notice */}
              <div className="p-3 bg-amber-500/10 border border-amber-500/25 rounded flex items-start space-x-2 text-amber-300 text-[11px]">
                <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-amber-400" />
                <span>
                  Ending this assignment will release the officer and preserve all historical telemetry
                  and event logs.
                </span>
              </div>

              {/* Optional Reason */}
              <div>
                <label className="block text-text-secondary font-bold text-[11px] mb-1">
                  Reason for ending assignment (optional)
                </label>
                <input
                  type="text"
                  value={endReason}
                  onChange={(e) => setEndReason(e.target.value)}
                  disabled={endingSubmitting}
                  placeholder="e.g. Shift conclusion / Handover rotation / Immersion complete"
                  className="w-full px-3 py-2 bg-elevated-2 border border-border-default rounded text-xs text-text-primary focus:outline-none focus:border-accent"
                />
              </div>

              {/* Error Display (Active Tracking Safety Block) */}
              {endError && (
                <div className="p-3 bg-rose-500/15 border border-rose-500/30 rounded flex items-start space-x-2 text-rose-300 text-xs">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                  <span>{endError}</span>
                </div>
              )}

              {/* Modal Actions */}
              <div className="pt-2 border-t border-border-subtle flex items-center justify-end space-x-3">
                <button
                  type="button"
                  onClick={handleCloseEndModal}
                  disabled={endingSubmitting}
                  className="px-4 py-2 rounded border border-border-default text-text-secondary hover:text-text-primary hover:bg-elevated-2 transition-colors cursor-pointer text-xs disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleConfirmEndAssignment}
                  disabled={endingSubmitting}
                  className="px-4 py-2 bg-rose-600 hover:bg-rose-500 disabled:opacity-50 text-white font-bold rounded transition-colors cursor-pointer text-xs flex items-center space-x-1.5 shadow-sm"
                >
                  {endingSubmitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  <span>{endingSubmitting ? 'Ending…' : 'End Assignment'}</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
