import { Idol, DashboardKPIs, ActiveMarker, TimestampLookupResult, JourneyData, User } from '../types';

const API_BASE = '/api/v1';

export async function fetchCurrentUser(): Promise<User | null> {
  try {
    const res = await fetch(`${API_BASE}/auth/me/`);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function fetchDashboardData(filters?: { zone?: string; police_station?: string }): Promise<{
  kpis: DashboardKPIs;
  active_markers_count: number;
  active_markers: ActiveMarker[];
}> {
  const params = new URLSearchParams();
  if (filters?.zone) params.append('zone', filters.zone);
  if (filters?.police_station) params.append('police_station', filters.police_station);

  const res = await fetch(`${API_BASE}/idols/dashboard/?${params.toString()}`);
  if (!res.ok) throw new Error('Failed to load dashboard metrics');
  return await res.json();
}

export async function fetchIdols(params?: {
  search?: string;
  zone?: string;
  police_station?: string;
  procession_state?: string;
  page?: number;
}): Promise<{ count: number; next: string | null; previous: string | null; results: Idol[] }> {
  const query = new URLSearchParams();
  if (params?.search) query.append('search', params.search);
  if (params?.zone) query.append('zone', params.zone);
  if (params?.police_station) query.append('police_station', params.police_station);
  if (params?.procession_state) query.append('procession_state', params.procession_state);
  if (params?.page) query.append('page', params.page.toString());

  const res = await fetch(`${API_BASE}/idols/?${query.toString()}`);
  if (!res.ok) throw new Error('Failed to load idols list');
  return await res.json();
}

export async function fetchIdolDetail(lookup: string): Promise<Idol> {
  const res = await fetch(`${API_BASE}/idols/${lookup}/`);
  if (!res.ok) throw new Error(`Idol with GPID ${lookup} not found`);
  return await res.json();
}

export async function fetchTimestampLookup(gpid: string, isoTimestamp: string): Promise<TimestampLookupResult> {
  const params = new URLSearchParams({ timestamp: isoTimestamp });
  const res = await fetch(`${API_BASE}/tracking/idols/${gpid}/location-at/?${params.toString()}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.message || err.error || 'No location point recorded for this timestamp.');
  }
  return await res.json();
}

export async function fetchJourney(gpid: string): Promise<JourneyData> {
  const res = await fetch(`${API_BASE}/tracking/idols/${gpid}/journey/`);
  if (!res.ok) throw new Error('Failed to fetch journey trail');
  return await res.json();
}

export function getReportDownloadUrl(gpid: string): string {
  return `${API_BASE}/reports/idols/${gpid}/`;
}

export async function assignConstable(gpid: string, constableId: number): Promise<any> {
  const res = await fetch(`${API_BASE}/assignments/create/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ gpid, constable_id: constableId }),
  });
  if (!res.ok) throw new Error('Failed to assign constable');
  return await res.json();
}

export async function handoverAssignment(assignmentId: number, newConstableId: number, reason: string): Promise<any> {
  const res = await fetch(`${API_BASE}/assignments/${assignmentId}/handover/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ new_constable_id: newConstableId, reason }),
  });
  if (!res.ok) throw new Error('Failed to handover duty');
  return await res.json();
}
