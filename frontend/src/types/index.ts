export type UserRole = 'SUPER_ADMIN' | 'MAIN_OFFICER' | 'SYS_ADMIN' | 'ACP' | 'SHO' | 'CONSTABLE';

export type ProcessionState =
  | 'NOT_STARTED'
  | 'TRACKING'
  | 'MOVING'
  | 'HOLDING'
  | 'AT_VISARJAN'
  | 'IMMERSION_COMPLETED';

export type ConnectionState = 'LIVE' | 'DEGRADED' | 'OFFLINE';

export interface User {
  id: number;
  username: string;
  name?: string;
  first_name?: string;
  last_name?: string;
  role: UserRole;
  police_id: string;
  zone: string;
  division: string;
  police_station: string;
  is_active?: boolean;
  must_change_password: boolean;
  permissions?: string[];
  custom_permissions?: string[];
  effective_permissions?: string[];
  date_joined?: string;
  role_display?: string;
  jurisdiction_display?: string;
}

export interface RolePermissionTemplate {
  id: number | null;
  role: UserRole;
  role_display: string;
  description: string;
  permissions: string[];
  user_count: number;
  updated_at: string | null;
  updated_by_name: string;
}

export interface AssignableOfficer {
  id: number;
  name: string;
  username: string;
  police_id: string;
  role: UserRole;
  police_station: string;
  zone?: string;
  is_active: boolean;
  currently_assigned: boolean;
  assigned_gpid: string | null;
}

export interface PoliceStationMaster {
  id: number;
  ps_name: string;
  ps_code: string;
  name?: string;
  code?: string;
  zone: string;
  division: string;
  first_unique_id?: string;
  starting_gpid_number?: number | null;
  has_boundary_polygon?: boolean;
}

export interface Idol {
  id: number;
  gpid: string;
  ref_no: string;
  name: string;
  association_name: string;
  dist_name: string;
  zone: string;
  division: string;
  police_station: string;
  ps_code: string;
  address: string;
  latitude?: number | null;
  longitude?: number | null;
  geocoding_status?: string;
  geocoding_confidence?: 'EXACT' | 'HIGH' | 'MEDIUM' | 'UNRESOLVED';
  geocoding_result_type?: string;
  resolved_address?: string;
  start_gate_eligible?: boolean;
  idol_height: number | null;
  height_classification?: 'GREEN' | 'YELLOW' | 'RED' | 'SUBTHRESHOLD';
  is_operational_eligible?: boolean;
  pandal_height: number | null;
  immersion_date: string | null;
  river_name: string;
  lake_type: string;
  idol_type: string;
  status: string;
  procession_state: ProcessionState;
  contact_info?: {
    mobile_no: string;
    email: string;
    member1: string;
    mob_member1: string;
    member2: string;
    mob_member2: string;
  };
  created_at: string;
  updated_at: string;
}

export interface ActiveMarker {
  id: number;
  tracking_session_id?: number;
  gpid: string;
  idol_name: string;
  association_name: string;
  zone: string;
  division: string;
  police_station: string;
  ps_code: string;
  procession_state: ProcessionState;
  connection_state: ConnectionState;
  is_origin_marker?: boolean;
  geocoding_status?: string;
  geocoding_confidence?: 'EXACT' | 'HIGH' | 'MEDIUM' | 'UNRESOLVED';
  geocoding_result_type?: string;
  resolved_address?: string;
  start_gate_eligible?: boolean;
  latitude: number;
  longitude: number;
  speed: number | null;
  heading: number | null;
  accuracy: number | null;
  last_gps_timestamp: string;
  idol_height?: number | null;
  height_classification?: 'GREEN' | 'YELLOW' | 'RED';
  immersion_date?: string | null;
  origin_location?: string;
  destination?: string;
  owner_name?: string;
  assigned_constable: {
    id: number;
    name: string;
    police_id: string;
    phone_number?: string | null;
  } | null;
}

export interface DashboardKPIs {
  total_idols: number; // 15+ FT GPIDs
  tracking_active: number;
  moving: number;
  holding: number;
  at_visarjan: number;
  immersion_completed: number;
  not_started: number;
  unassigned: number;
  offline_or_degraded: number;
  immersions_today: number;
  h_15_20?: number;
  h_21_25?: number;
  h_26_plus?: number;
}

export interface TimestampLookupResult {
  gpid: string;
  idol_name: string;
  target_timestamp: string;
  nearest_point: {
    id: number;
    latitude: number;
    longitude: number;
    accuracy: number | null;
    speed: number | null;
    heading: number | null;
    recorded_at: string;
    time_difference_seconds: number;
  };
  session_id: number;
  constable: {
    id: number;
    username: string;
    name: string;
    police_id: string;
  };
}

export interface JourneyBreadcrumb {
  latitude: number;
  longitude: number;
  speed: number | null;
  heading: number | null;
  accuracy: number | null;
  recorded_at: string;
}

export interface IdolTimelineEvent {
  id: number;
  event_type: string;
  label: string;
  timestamp: string;
  latitude: number | null;
  longitude: number | null;
  zone: string;
  actor: string | null;
  metadata?: Record<string, any>;
}

export interface JourneyData {
  gpid: string;
  tracking_session_id?: number;
  idol_name: string;
  police_station: string;
  zone: string;
  procession_state: ProcessionState;
  connection_state: ConnectionState;
  total_points: number;
  distance_travelled_km?: number | null;
  events?: IdolTimelineEvent[];
  summary: {
    start_time: string | null;
    end_time: string | null;
    max_speed_kmh: number;
  };
  points: JourneyBreadcrumb[];
}

export interface Assignment {
  id: number;
  idol: number;
  idol_gpid: string;
  idol_name: string;
  police_station: string;
  constable: number;
  constable_name: string;
  constable_username: string;
  constable_police_id: string;
  assigned_by: number | null;
  started_at: string;
  ended_at: string | null;
  is_active: boolean;
  handover_reason: string;
  handover_to: number | null;
  created_at: string;
}

export type HeightBucketFilter = 'all' | 'all_heights' | 'below_15' | '15_20' | '21_25' | '26_plus' | 'all_15_plus';
export type AssignmentStatusFilter = 'all' | 'unassigned' | 'assigned';
export type VisarjanDateFilter = 'all' | 'today' | 'tomorrow' | string;

export interface AssignableIdol {
  id: number;
  gpid: string;
  name: string;
  association_name: string;
  idol_height: number;
  height: number;
  height_bucket: 'below_15' | '15-20' | '21-25' | '26+' | string;
  height_classification: 'GREEN' | 'YELLOW' | 'RED' | 'SUBTHRESHOLD' | 'UNKNOWN' | string;
  zone: string;
  division: string;
  police_station: string;
  ps_code: string;
  address: string;
  latitude?: number | null;
  longitude?: number | null;
  geocoding_confidence?: string;
  resolved_address?: string;
  visarjan_date?: string | null;
  immersion_date?: string | null;
  procession_state: ProcessionState;
  tracking_state: ConnectionState;
  assignment: {
    id: number;
    status: 'ACTIVE';
    officer_name: string;
    officer_id: number;
    police_id: string;
    police_station: string;
    started_at: string;
  } | null;
}

export interface AssignableSummary {
  total_eligible: number;
  count_below_15?: number;
  count_15_20: number;
  count_21_25: number;
  count_26_plus: number;
  assigned: number;
  unassigned: number;
}

export interface AssignableRegistryResponse {
  count: number;
  next: string | null;
  previous: string | null;
  summary: AssignableSummary;
  results: AssignableIdol[];
}

export interface AssignableIdolDetail {
  id: number;
  gpid: string;
  name: string;
  association_name: string;
  idol_height: number;
  height_bucket: 'below_15' | '15-20' | '21-25' | '26+' | string;
  height_classification: 'GREEN' | 'YELLOW' | 'RED' | 'SUBTHRESHOLD' | 'UNKNOWN' | string;
  zone: string;
  division: string;
  police_station: string;
  ps_code: string;
  address: string;
  latitude?: number | null;
  longitude?: number | null;
  destination: string;
  visarjan_date?: string | null;
  immersion_date?: string | null;
  procession_state: ProcessionState;
  connection_state: ConnectionState;
  last_gps_timestamp?: string | null;
  assignment: {
    id: number;
    status: 'ACTIVE';
    officer_name: string;
    officer_id: number;
    police_id: string;
    police_station: string;
    phone_number?: string | null;
    started_at: string;
  } | null;
  contact_info?: {
    mobile_no: string;
    email: string;
  } | null;
  milestones: {
    assigned?: string | null;
    reached_site?: string | null;
    procession_started?: string | null;
    reached_visarjan?: string | null;
    visarjan_completed?: string | null;
    returned_to_origin?: string | null;
  };
  events: Array<{
    id: number;
    event_type: string;
    label: string;
    timestamp: string;
    zone: string;
    actor?: string | null;
    metadata?: Record<string, any>;
  }>;
}

export interface EligibleOfficer {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
  name: string;
  police_id: string;
  police_station: string;
  zone: string;
  phone_number?: string;
  availability: string;
}

export interface EligibleOfficersResponse {
  gpid: string;
  idol_name: string;
  zone: string;
  police_station: string;
  visarjan_date?: string | null;
  is_already_assigned: boolean;
  current_assignment?: {
    id: number;
    username: string;
    full_name: string;
    police_id: string;
    phone_number: string;
    police_station: string;
    zone: string;
    started_at: string | null;
  } | null;
  total_eligible: number;
  officers: EligibleOfficer[];
}

export interface CompletedReportItem {
  id: number;
  gpid: string;
  name: string;
  association_name: string;
  idol_height: number;
  zone: string;
  division: string;
  police_station: string;
  immersion_date: string | null;
  procession_state: string;
  final_state: 'IMMERSION_COMPLETED' | 'SENT_TO_HOLDING' | string;
  final_state_display: string;
  assigned_officer?: {
    id: number | null;
    name: string;
    username: string;
    police_id: string;
    is_active: boolean;
  } | null;
  report_download_url: string;
  completed_at: string | null;
}

export interface CompletedReportsSummary {
  total_eligible: number;
  count_completed: number;
  count_holding: number;
  count_15_20: number;
  count_21_25: number;
  count_26_plus: number;
}

export interface CompletedReportsResponse {
  count: number;
  next: string | null;
  previous: string | null;
  summary: CompletedReportsSummary;
  results: CompletedReportItem[];
}

