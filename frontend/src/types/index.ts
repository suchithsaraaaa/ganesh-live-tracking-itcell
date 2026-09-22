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
  role: UserRole;
  police_id: string;
  zone: string;
  division: string;
  police_station: string;
  must_change_password: boolean;
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
  assigned_constable: {
    id: number;
    name: string;
    police_id: string;
    phone_number: string;
  } | null;
}

export interface DashboardKPIs {
  total_idols: number;
  tracking_active: number;
  moving: number;
  holding: number;
  at_visarjan: number;
  immersion_completed: number;
  not_started: number;
  unassigned: number;
  offline_or_degraded: number;
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

export interface JourneyData {
  gpid: string;
  idol_name: string;
  police_station: string;
  zone: string;
  procession_state: ProcessionState;
  connection_state: ConnectionState;
  total_points: number;
  summary: {
    start_time: string | null;
    end_time: string | null;
    max_speed_kmh: number;
  };
  points: JourneyBreadcrumb[];
}
