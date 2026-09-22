export type UserRole = 'MAIN_OFFICER' | 'ACP' | 'SHO' | 'CONSTABLE';

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
  date_joined?: string;
}

export interface AssignableOfficer {
  id: number;
  name: string;
  username: string;
  police_id: string;
  role: UserRole;
  police_station: string;
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
  gpid: string;
  idol_name: string;
  association_name: string;
  zone: string;
  division: string;
  police_station: string;
  ps_code: string;
  procession_state: ProcessionState;
  connection_state: ConnectionState;
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
