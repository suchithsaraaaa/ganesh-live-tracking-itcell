import {
  Idol,
  DashboardKPIs,
  ActiveMarker,
  TimestampLookupResult,
  JourneyData,
  User,
  Assignment,
  AssignableRegistryResponse,
  AssignableIdolDetail
} from '../types';

const API_BASE = '/api/v1';

function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'));
  return match ? decodeURIComponent(match[1]) : null;
}

/**
 * Wraps fetch() with the session-cookie + CSRF conventions the Django backend expects:
 * same-origin credentials on every call, and an X-CSRFToken header on unsafe methods
 * whenever the browser holds a csrftoken cookie.
 */
async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const method = (options.method || 'GET').toUpperCase();
  const headers = new Headers(options.headers);

  if (!['GET', 'HEAD', 'OPTIONS', 'TRACE'].includes(method)) {
    const csrfToken = getCookie('csrftoken');
    if (csrfToken) headers.set('X-CSRFToken', csrfToken);
  }

  return fetch(`${API_BASE}${path}`, {
    ...options,
    method,
    headers,
    credentials: 'same-origin',
  });
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

// ---------------------------------------------------------------------------
// Authentication
// ---------------------------------------------------------------------------

export async function login(username: string, password: string): Promise<User> {
  const res = await apiFetch('/auth/login/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new ApiError(data.error || 'Invalid credentials.', res.status);
  }
  return data;
}

export async function logout(): Promise<void> {
  await apiFetch('/auth/logout/', { method: 'POST' });
}

export async function fetchCurrentUser(): Promise<User | null> {
  try {
    const res = await apiFetch('/auth/me/');
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Dashboard & Idols
// ---------------------------------------------------------------------------

export async function fetchDashboardData(filters?: {
  zone?: string;
  police_station?: string;
  height_bucket?: string;
  immersion_date?: string;
  immersions_today?: boolean;
}): Promise<{
  kpis: DashboardKPIs;
  active_markers_count: number;
  active_markers: ActiveMarker[];
}> {
  const params = new URLSearchParams();
  if (filters?.zone) params.append('zone', filters.zone);
  if (filters?.police_station) params.append('police_station', filters.police_station);
  if (filters?.height_bucket && filters.height_bucket !== 'ALL') params.append('height_bucket', filters.height_bucket);
  if (filters?.immersion_date) params.append('immersion_date', filters.immersion_date);
  if (filters?.immersions_today) params.append('immersions_today', 'true');

  const res = await apiFetch(`/idols/dashboard/?${params.toString()}`);
  if (!res.ok) throw new ApiError('Failed to load dashboard metrics', res.status);
  return await res.json();
}

export async function fetchIdols(params?: {
  search?: string;
  zone?: string;
  police_station?: string;
  procession_state?: string;
  height_bucket?: string;
  min_height?: number;
  max_height?: number;
  immersion_date?: string;
  immersions_today?: boolean;
  page?: number;
}): Promise<{ count: number; next: string | null; previous: string | null; results: Idol[] }> {
  const query = new URLSearchParams();
  if (params?.search) query.append('search', params.search);
  if (params?.zone) query.append('zone', params.zone);
  if (params?.police_station) query.append('police_station', params.police_station);
  if (params?.procession_state) query.append('procession_state', params.procession_state);
  if (params?.height_bucket && params.height_bucket !== 'ALL') query.append('height_bucket', params.height_bucket);
  if (params?.min_height !== undefined) query.append('min_height', params.min_height.toString());
  if (params?.max_height !== undefined) query.append('max_height', params.max_height.toString());
  if (params?.immersion_date) query.append('immersion_date', params.immersion_date);
  if (params?.immersions_today) query.append('immersions_today', 'true');
  if (params?.page) query.append('page', params.page.toString());

  const res = await apiFetch(`/idols/?${query.toString()}`);
  if (!res.ok) throw new ApiError('Failed to load idols list', res.status);
  return await res.json();
}

export async function fetchIdolDetail(lookup: string): Promise<Idol> {
  const res = await apiFetch(`/idols/${lookup}/`);
  if (!res.ok) throw new ApiError(`Idol with GPID ${lookup} not found`, res.status);
  return await res.json();
}

// ---------------------------------------------------------------------------
// Tracking / Journey
// ---------------------------------------------------------------------------

export async function fetchTimestampLookup(gpid: string, isoTimestamp: string): Promise<TimestampLookupResult> {
  const params = new URLSearchParams({ timestamp: isoTimestamp });
  const res = await apiFetch(`/tracking/idols/${gpid}/location-at/?${params.toString()}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new ApiError(err.message || err.error || 'No location point recorded for this timestamp.', res.status);
  }
  return await res.json();
}

export async function fetchJourney(gpid: string, sessionId?: number): Promise<JourneyData> {
  const query = sessionId ? `?session_id=${sessionId}` : '';
  const res = await apiFetch(`/tracking/idols/${gpid}/journey/${query}`);
  if (!res.ok) throw new ApiError('Failed to fetch journey trail', res.status);
  return await res.json();
}

export async function fetchSessionJourney(sessionId: number): Promise<JourneyData> {
  const res = await apiFetch(`/tracking/sessions/${sessionId}/journey/`);
  if (!res.ok) throw new ApiError('Failed to fetch session journey trail', res.status);
  return await res.json();
}

export async function fetchActiveTrackingMarkers(filters?: {
  zone?: string;
  police_station?: string;
  height_bucket?: string;
  search?: string;
}): Promise<ActiveMarker[]> {
  const query = new URLSearchParams();
  if (filters?.zone && filters.zone !== 'All Zones') query.append('zone', filters.zone);
  if (filters?.police_station) query.append('police_station', filters.police_station);
  if (filters?.height_bucket && filters.height_bucket !== 'ALL') query.append('height_bucket', filters.height_bucket);
  if (filters?.search) query.append('search', filters.search);

  const res = await apiFetch(`/tracking/active/?${query.toString()}`);
  if (!res.ok) throw new ApiError('Failed to fetch active tracking markers', res.status);
  return await res.json();
}

// ---------------------------------------------------------------------------
// Reports
// ---------------------------------------------------------------------------

export function getReportDownloadUrl(gpid: string, sessionId?: number): string {
  const query = sessionId ? `?session_id=${sessionId}` : '';
  return `${API_BASE}/reports/idols/${gpid}/${query}`;
}

export async function fetchCompletedReportsRegistry(params?: {
  page?: number;
  page_size?: number;
  search?: string;
  zone?: string;
  police_station?: string;
  visarjan_date?: string;
  height_bucket?: string;
  operational_status?: string;
  ordering?: string;
}): Promise<import('../types').CompletedReportsResponse> {
  const query = new URLSearchParams();
  if (params?.page) query.append('page', params.page.toString());
  if (params?.page_size) query.append('page_size', params.page_size.toString());
  if (params?.search) query.append('search', params.search);
  if (params?.zone && params.zone !== 'all' && params.zone !== 'All Zones') query.append('zone', params.zone);
  if (params?.police_station && params.police_station !== 'all' && params.police_station !== 'All Police Stations') {
    query.append('police_station', params.police_station);
  }
  if (params?.visarjan_date && params.visarjan_date !== 'all' && params.visarjan_date !== 'All Dates') {
    query.append('visarjan_date', params.visarjan_date);
  }
  if (params?.height_bucket && params.height_bucket !== 'all' && params.height_bucket !== 'All 15+ FT') {
    query.append('height_bucket', params.height_bucket);
  }
  if (params?.operational_status && params.operational_status !== 'all') {
    query.append('operational_status', params.operational_status);
  }
  if (params?.ordering) query.append('ordering', params.ordering);

  const res = await apiFetch(`/reports/registry/?${query.toString()}`);
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new ApiError(data.error || data.detail || 'Failed to load completed reports registry', res.status);
  }
  return await res.json();
}



// ---------------------------------------------------------------------------
// Assignments
// ---------------------------------------------------------------------------

export async function fetchAssignments(page?: number): Promise<{ count: number; next: string | null; previous: string | null; results: Assignment[] }> {
  const query = new URLSearchParams();
  if (page) query.append('page', page.toString());
  const res = await apiFetch(`/assignments/?${query.toString()}`);
  if (!res.ok) throw new ApiError('Failed to load assignments', res.status);
  return await res.json();
}

export async function fetchAssignableRegistry(params?: {
  page?: number;
  page_size?: number;
  zone?: string;
  police_station?: string;
  height_bucket?: string;
  assignment_status?: string;
  visarjan_date?: string;
  search?: string;
  ordering?: string;
}): Promise<AssignableRegistryResponse> {
  const query = new URLSearchParams();
  if (params?.page) query.append('page', params.page.toString());
  if (params?.page_size) query.append('page_size', params.page_size.toString());
  if (params?.zone && params.zone !== 'All Zones') query.append('zone', params.zone);
  if (params?.police_station && params.police_station !== 'All Police Stations') query.append('police_station', params.police_station);
  if (params?.height_bucket && params.height_bucket !== 'All 15+ FT') query.append('height_bucket', params.height_bucket);
  if (params?.assignment_status && params.assignment_status !== 'all') query.append('assignment_status', params.assignment_status);
  if (params?.visarjan_date && params.visarjan_date !== 'all' && params.visarjan_date !== 'All Dates') query.append('visarjan_date', params.visarjan_date);
  if (params?.search) query.append('search', params.search);
  if (params?.ordering) query.append('ordering', params.ordering);

  const res = await apiFetch(`/assignments/registry/?${query.toString()}`);
  if (!res.ok) throw new ApiError('Failed to load assignable idols registry', res.status);
  return await res.json();
}

export async function fetchAssignableIdolDetail(gpid: string): Promise<AssignableIdolDetail> {
  const res = await apiFetch(`/assignments/registry/${encodeURIComponent(gpid)}/`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new ApiError(err.error || `Failed to load details for ${gpid}`, res.status);
  }
  return await res.json();
}

export function getAssignmentExcelExportUrl(params?: {
  zone?: string;
  police_station?: string;
  height_bucket?: string;
  assignment_status?: string;
  visarjan_date?: string;
  search?: string;
}): string {
  const query = new URLSearchParams();
  if (params?.zone && params.zone !== 'All Zones') query.append('zone', params.zone);
  if (params?.police_station && params.police_station !== 'All Police Stations') query.append('police_station', params.police_station);
  if (params?.height_bucket && params.height_bucket !== 'All 15+ FT') query.append('height_bucket', params.height_bucket);
  if (params?.assignment_status && params.assignment_status !== 'all') query.append('assignment_status', params.assignment_status);
  if (params?.visarjan_date && params.visarjan_date !== 'all' && params.visarjan_date !== 'All Dates') query.append('visarjan_date', params.visarjan_date);
  if (params?.search) query.append('search', params.search);

  return `${API_BASE}/assignments/export/?${query.toString()}`;
}

export async function assignConstable(gpid: string, constableId: number): Promise<Assignment> {
  const res = await apiFetch('/assignments/create/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ gpid, constable_id: constableId }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(data.error || summarizeFieldErrors(data) || 'Failed to assign constable', res.status);
  return data;
}

export async function handoverAssignment(assignmentId: number, newConstableId: number, reason: string): Promise<any> {
  const res = await apiFetch(`/assignments/${assignmentId}/handover/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ new_constable_id: newConstableId, reason }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(data.error || summarizeFieldErrors(data) || 'Failed to handover duty', res.status);
  return data;
}

export async function endAssignment(
  assignmentId: number,
  reason?: string,
  force?: boolean
): Promise<{ message: string; assignment: Assignment; tracking_terminated?: boolean }> {
  const res = await apiFetch(`/assignments/${assignmentId}/end/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason: reason || '', force: force ?? false }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const errorMsg =
      data.error ||
      data.detail ||
      data.message ||
      (res.status === 403
        ? 'Permission denied. Administrative privilege required to force-end.'
        : res.status === 404
        ? 'Assignment not found.'
        : res.status === 500
        ? 'Internal server error (500). Please check backend logs.'
        : `Failed to end assignment (HTTP ${res.status})`);
    throw new ApiError(errorMsg, res.status);
  }
  return data;
}

// ---------------------------------------------------------------------------
// User Management (Administrative)
// ---------------------------------------------------------------------------

export async function fetchUsers(params?: {
  search?: string;
  role?: string;
  is_active?: boolean;
  police_station?: string;
}): Promise<{ count: number; results: User[] }> {
  const query = new URLSearchParams();
  if (params?.search) query.append('search', params.search);
  if (params?.role) query.append('role', params.role);
  if (params?.is_active !== undefined) query.append('is_active', String(params.is_active));
  if (params?.police_station) query.append('police_station', params.police_station);

  const res = await apiFetch(`/auth/users/?${query.toString()}`);
  if (!res.ok) throw new ApiError('Failed to load user accounts', res.status);
  return await res.json();
}

export async function createUser(userData: Partial<User> & { password?: string }): Promise<User> {
  const res = await apiFetch('/auth/users/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(userData),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(data.error || summarizeFieldErrors(data) || 'Failed to create user', res.status);
  return data;
}

export async function updateUser(id: number, userData: Partial<User> & { password?: string }): Promise<User> {
  const res = await apiFetch(`/auth/users/${id}/`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(userData),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(data.error || summarizeFieldErrors(data) || 'Failed to update user', res.status);
  return data;
}

export async function toggleUserActive(id: number): Promise<{ id: number; username: string; is_active: boolean; message: string }> {
  const res = await apiFetch(`/auth/users/${id}/toggle-active/`, {
    method: 'POST',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(data.error || 'Failed to toggle user status', res.status);
  return data;
}

export async function deleteUser(id: number): Promise<{ message: string }> {
  const res = await apiFetch(`/auth/users/${id}/delete/`, {
    method: 'DELETE',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(data.error || 'Failed to delete user account', res.status);
  return data;
}


// ---------------------------------------------------------------------------
// Field Officers Directory
// ---------------------------------------------------------------------------

export async function fetchAssignableOfficers(options?: {
  policeStation?: string;
  availableOnly?: boolean;
} | string): Promise<{ count: number; results: import('../types').AssignableOfficer[] }> {
  const query = new URLSearchParams();
  if (typeof options === 'string') {
    if (options) query.append('police_station', options);
  } else if (options) {
    if (options.policeStation) query.append('police_station', options.policeStation);
    if (options.availableOnly) query.append('available_only', 'true');
  }

  const res = await apiFetch(`/auth/officers/?${query.toString()}`);
  if (!res.ok) throw new ApiError('Failed to load assignable field officers', res.status);
  return await res.json();
}

export async function fetchEligibleOfficersForGpid(gpid: string): Promise<import('../types').EligibleOfficersResponse> {
  const res = await apiFetch(`/assignments/registry/${encodeURIComponent(gpid)}/eligible-officers/`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new ApiError(err.error || `Failed to load eligible officers for ${gpid}`, res.status);
  }
  return await res.json();
}

// ---------------------------------------------------------------------------
// Authoritative Geography
// ---------------------------------------------------------------------------

export async function fetchAuthoritativeZones(): Promise<string[]> {
  const res = await apiFetch('/geography/zones/');
  if (!res.ok) throw new ApiError('Failed to load authoritative zones', res.status);
  const data = await res.json();
  return data.zones || [];
}

export async function fetchAuthoritativePoliceStations(zone?: string): Promise<{ count: number; results: import('../types').PoliceStationMaster[] }> {
  const query = new URLSearchParams();
  if (zone && zone !== 'All Zones' && zone !== 'All' && zone.trim() !== '') {
    query.append('zone', zone.trim());
  }
  const res = await apiFetch(`/geography/police-stations/?${query.toString()}`);
  if (!res.ok) throw new ApiError('Failed to load authoritative police stations', res.status);
  return await res.json();
}

// ---------------------------------------------------------------------------
// Latest Location
// ---------------------------------------------------------------------------

export async function fetchLatestLocation(gpid: string): Promise<any> {
  const res = await apiFetch(`/tracking/idols/${gpid}/latest/`);
  if (!res.ok) throw new ApiError(`Failed to load latest location for ${gpid}`, res.status);
  return await res.json();
}

function summarizeFieldErrors(data: any): string | null {
  if (!data || typeof data !== 'object') return null;
  const parts: string[] = [];
  for (const [field, val] of Object.entries(data)) {
    if (Array.isArray(val)) parts.push(`${field}: ${val.join(', ')}`);
  }
  return parts.length > 0 ? parts.join(' | ') : null;
}
