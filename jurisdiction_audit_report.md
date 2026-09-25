# Jurisdiction & RBAC Forensic Audit

## Executive Summary

- **Audit Timestamp**: 2026-09-25 12:45:00 IST
- **Current Commit**: `c3f33e0` ("fix(jurisdiction): normalize PS and zone matching and fix end assignment authorization")
- **Deployment Baseline**: EC2 Production Host `15.206.58.226` (Django backend container `ganesh-live-tracking-itcell-backend-1`, Nginx `ganesh-live-tracking-itcell-nginx-1`, PostGIS DB `ganesh-live-tracking-itcell-db-1`)
- **Audit Objective**: High-signal forensic triage of all backend authorization, role-based access control, centralized jurisdiction helper coverage, and direct API bypass vulnerabilities across the Hyderabad Police Ganesh Visarjan Live Tracking System.

---

## Overall Status

- **CRITICAL**: 2 (Telemetry control & lifecycle spoofing without ownership checks; unauthenticated public mobile compatibility endpoints with auto-assignment fallback)
- **HIGH**: 3 (Duty Handover lacks jurisdiction & role guards and blocks Super/Sys Admins; Start Tracking blocks Super/Sys Admins and allows cross-jurisdiction station officers; Officer account creation fails on spaced station names)
- **MEDIUM**: 2 (Raw `police_station__iexact` query filter used across Dashboard, Live Map, Reports, and User Management; Constable boundary queryset model fallback anomaly)
- **LOW**: 1 (Redundant role check patterns in legacy utility methods)

---

## 1. Confirmed Bugs

### BUG-JUR-001
- **Severity**: CRITICAL
- **System**: Live Telemetry & Procession Event Ingestion
- **Endpoint/File**:
  - `POST /api/v1/tracking/location/` (`IngestLocationView`, `backend/apps/tracking/views.py:160-220`)
  - `POST /api/v1/tracking/location/batch/` (`BatchIngestLocationView`, `backend/apps/tracking/views.py:221-285`)
  - `POST /api/v1/tracking/stop/` (`StopTrackingView`, `backend/apps/tracking/views.py:286-378`)
  - `POST /api/v1/tracking/events/` (`ProcessionEventIngestView`, `backend/apps/tracking/views.py:972-1065`)
- **Current Behavior**: Any authenticated user can submit GPS coordinates to any active tracking session, terminate any tracking session across the entire city, or force an idol's state to `IMMERSION_COMPLETED`, `HOLDING`, or `NOT_STARTED`.
- **Expected Behavior**: Only the constable assigned to the tracking session (or an authorized administrative officer with verified jurisdiction over the idol) must be permitted to ingest GPS telemetry, terminate tracking, or log lifecycle events.
- **Root Cause**: Neither `IngestLocationView`, `BatchIngestLocationView`, `StopTrackingView`, nor `ProcessionEventIngestView` verifies `request.user == session.assignment.constable` or calls `check_user_jurisdiction_over_idol(request.user, idol)`.
- **Security Impact**: Telemetry spoofing, cross-procession stoppage, and falsification of official immersion completion status.
- **User Impact**: Ground staff or malicious actors can tamper with other stations' active processions.
- **Recommended Fix**: Add mandatory constable ownership check with fallback to `check_user_jurisdiction_over_idol(request.user, idol)` on all four endpoints.

---

### BUG-JUR-002
- **Severity**: CRITICAL
- **System**: Legacy Android Compatibility Routes
- **Endpoint/File**:
  - `POST /api/tracking/session` (`MobileSessionView`, `backend/apps/tracking/views.py:807-900`)
  - `POST /api/tracking/location` (`MobileLocationView`, `backend/apps/tracking/views.py:901-970`)
  - Registered in `backend/config/urls.py:22-23`
- **Current Behavior**: Both routes have `permission_classes = []`. Any unauthenticated HTTP client can invoke `POST /api/tracking/session`. If user credentials are missing, line 829 falls back to the first available constable in the database, and line 857 calls `Assignment.assign_constable(idol=Idol.objects.first(), constable=user)`, automatically creating real assignments on production data.
- **Expected Behavior**: All mobile API endpoints must require authentication (`[IsAuthenticated]`), identify the caller from request credentials, and prohibit unauthenticated auto-assignments.
- **Root Cause**: Legacy mock/scaffolding endpoints left with `permission_classes = []` and development auto-provisioning enabled outside `DEBUG` guard.
- **Security Impact**: Unauthenticated database mutation, arbitrary assignment creation, and unauthorized telemetry injection.
- **User Impact**: Public requests can trigger spurious assignments and corrupt tracking state.
- **Recommended Fix**: Enforce `permission_classes = [IsAuthenticated]`, validate token/caller identity, and remove `Idol.objects.first()` auto-assignment fallbacks in production.

---

### BUG-JUR-003
- **Severity**: HIGH
- **System**: Duty Handover
- **Endpoint/File**: `POST /api/v1/assignments/<pk>/handover/` (`HandoverAssignmentView`, `backend/apps/assignments/views.py:68-107`) and `HandoverSerializer` (`backend/apps/assignments/serializers.py:131-140`)
- **Current Behavior**:
  1. `SUPER_ADMIN` and `SYS_ADMIN` receive `403 Forbidden` ("You do not have permission to handover this duty.") because line 84 hardcodes `request.user.role not in ['MAIN_OFFICER', 'ACP', 'SHO']`.
  2. Any `SHO` or `ACP` from any station/zone in the city can handover assignments belonging to unrelated jurisdictions because line 84 does not verify jurisdiction over `assignment.idol`.
  3. `HandoverSerializer` only checks if `new_constable_id` exists in `User`. It does not verify that the new user is active, has the `CONSTABLE` role, or matches the idol's zone and police station.
- **Expected Behavior**: `SUPER_ADMIN`, `MAIN_OFFICER`, authorized `SYS_ADMIN`/`ACP`/`SHO` with jurisdiction over the idol, or the assigned constable can execute handovers. Target officer must be active, have `CONSTABLE` role, and belong to the same canonical police station and zone.
- **Root Cause**: Omission of `SUPER_ADMIN`/`SYS_ADMIN` in role checks, absence of `check_user_jurisdiction_over_idol`, and lack of validation rules in `HandoverSerializer`.
- **Security Impact**: Station officers can reassign idols outside their jurisdiction; idols can be handed over to non-constable or cross-station users.
- **User Impact**: Super Admins cannot execute administrative handovers; invalid officer handovers can disrupt operations.
- **Recommended Fix**: Integrate `check_user_jurisdiction_over_idol` into `HandoverAssignmentView` and validate `new_constable` with `are_same_ps` and `are_same_zone` in `HandoverSerializer`.

---

### BUG-JUR-004
- **Severity**: HIGH
- **System**: Tracking Session Initiation
- **Endpoint/File**: `POST /api/v1/tracking/start/` (`StartTrackingView`, `backend/apps/tracking/views.py:80-158`)
- **Current Behavior**:
  1. `SUPER_ADMIN` and `SYS_ADMIN` receive `403 Forbidden` because line 93 checks `request.user.role not in ['MAIN_OFFICER', 'ACP', 'SHO']`.
  2. Station officers (`SHO`, `ACP`) from other zones or police stations can start tracking sessions for any idol citywide without jurisdiction checks.
- **Expected Behavior**: Assigned constable, `SUPER_ADMIN`, citywide `MAIN_OFFICER`, or authorized Zonal/Station officer having jurisdiction over `assignment.idol` can start tracking.
- **Root Cause**: Role check `request.user.role not in ['MAIN_OFFICER', 'ACP', 'SHO']` omits `SUPER_ADMIN`/`SYS_ADMIN` and lacks `check_user_jurisdiction_over_idol` validation.
- **Security Impact**: Cross-jurisdiction operational trigger by unauthorized station officers.
- **User Impact**: Super Admins and System Admins cannot initiate tracking on behalf of an assignment.
- **Recommended Fix**: Update line 93 to use `check_user_jurisdiction_over_idol(request.user, assignment.idol)` or verify assigned constable identity.

---

### BUG-JUR-005
- **Severity**: HIGH
- **System**: User Management (Officer Creation & Updates)
- **Endpoint/File**: `POST /api/v1/auth/users/` & `PATCH /api/v1/auth/users/<pk>/` (`UserCreateUpdateSerializer`, `backend/apps/accounts/serializers.py:310, 325, 340`)
- **Current Behavior**: When creating or updating a `CONSTABLE` or `SHO`, the serializer runs `PoliceStationBoundary.objects.filter(ps_name__iexact=police_station).first()`. If `police_station` is `'Rajendra Nagar'` (or spaced variants like `'Bhavani Nagar'`), the query returns `None` because the boundary record is `'Rajendranagar'` (no space). Serializer rejects valid input with `"Police station 'Rajendra Nagar' is not a recognized authoritative station."`
- **Expected Behavior**: Validates police station names against `PoliceStationBoundary` using canonical normalization (`ps_filter_q` or `are_same_ps`).
- **Root Cause**: Exact string match `ps_name__iexact=police_station` against boundary table without canonical alias normalization.
- **Security Impact**: Low (security boundaries remain intact).
- **User Impact**: Administrators cannot create or update officers for Rajendra Nagar station using its spaced representation.
- **Recommended Fix**: Replace `ps_name__iexact=police_station` with `ps_filter_q('ps_name', police_station)` in `UserCreateUpdateSerializer`.

---

## 2. Potential Issues

### POT-JUR-001
- **Severity**: MEDIUM
- **System**: Query Filtering Across 4 Operational Views
- **Endpoint/File**:
  - `GET /api/v1/idols/` & `GET /api/v1/idols/dashboard/` (`apps/idols/views.py:151`)
  - `GET /api/v1/tracking/active/` (`apps/tracking/views.py:654`)
  - `GET /api/v1/reports/registry/` (`apps/reports/views.py:85`)
  - `GET /api/v1/auth/users/` (`apps/accounts/views.py:83`)
- **Current Behavior**: All four views filter user-provided query parameters using raw `police_station__iexact=ps`. When a user selects `'Rajendra Nagar'`, records stored as `'Rajendranagar'` are dropped.
- **Expected Behavior**: Query filtering should use `ps_filter_q('police_station', ps)` to capture both canonical and legacy representations.
- **Root Cause**: Incomplete rollout of `ps_filter_q` outside `assignments/views.py`.
- **Security Impact**: No security bypass (data is over-filtered, not leaked).
- **User Impact**: Legitimate idols, tracking sessions, reports, and users are omitted when filtering by station name.
- **Recommended Fix**: Adopt `ps_filter_q` in all four views.

---

### POT-JUR-002
- **Severity**: MEDIUM
- **System**: Centralized Permission Helper (Constable Boundary Fallback)
- **Endpoint/File**: `common/permissions.py:124-138` (`filter_by_jurisdiction`)
- **Current Behavior**: If a `CONSTABLE` queries `PoliceStationBoundary` through `filter_by_jurisdiction`, the helper does not check `model_name == 'PoliceStationBoundary'` and executes `return queryset.filter(id__in=assigned_idol_ids)`, filtering boundary records by idol IDs.
- **Expected Behavior**: Boundary queries should return the constable's assigned station boundary or `queryset.none()`.
- **Root Cause**: Missing explicit `model_name == 'PoliceStationBoundary'` check in constable branch.
- **Security Impact**: Minimal (does not expose unauthorized data).
- **User Impact**: Potential empty results for constables inspecting boundary geometry.
- **Recommended Fix**: Add explicit model handling for `PoliceStationBoundary` in `filter_by_jurisdiction`.

---

## 3. Systems Audited

| System | Backend Enforcement | Centralized Helper | Direct API Risk | Status |
|---|---|---|---|---|
| **A. Assignment Registry** | YES (`filter_by_jurisdiction`) | YES (`zone_filter_q`, `ps_filter_q`) | PASS (No bypass possible) | PASS |
| **B. Assignment Creation** | YES (`CreateAssignmentSerializer`) | YES (`check_user_jurisdiction_over_idol`, `are_same_ps`, `are_same_zone`) | PASS (Strict validation) | PASS |
| **C. Officer Eligibility** | YES (`AssignableEligibleOfficersView`) | YES (`filter_by_jurisdiction`, `zone_filter_q`, `ps_filter_q`) | PASS (Scoped to GPID jurisdiction) | PASS |
| **D. End Assignment** | YES (`EndAssignmentView`) | YES (`check_user_jurisdiction_over_idol`) | PASS (Properly restricts non-admins) | PASS |
| **E. Force End (Admin)** | YES (`EndAssignmentView`) | YES (`is_admin` includes `SUPER_ADMIN`, `MAIN_OFFICER`, `SYS_ADMIN`) | PASS (Atomic termination) | PASS |
| **F. Duty Handover** | PARTIAL (`HandoverAssignmentView`) | NO (Hardcoded roles, no idol jurisdiction check, unvalidated constable) | FAIL (Cross-PS handover possible; Super Admin blocked) | BUG-JUR-003 |
| **G. User Management** | YES (`CanManageUsers`, `filter_by_jurisdiction`) | PARTIAL (Boundary validation uses raw `ps_name__iexact`) | FAIL for officer creation with spaced PS | BUG-JUR-005 |
| **H. Reports Registry** | YES (`filter_by_jurisdiction`) | PARTIAL (Query filter uses raw `police_station__iexact`) | PASS (Security intact; PS filter drops variants) | POT-JUR-001 |
| **I. Report Detail / PDF** | YES (`DownloadIdolReportView`) | YES (`filter_by_jurisdiction`) | PASS (404 on cross-jurisdiction GPID) | PASS |
| **J. Live Tracking (Active)** | YES (`filter_by_jurisdiction`) | PARTIAL (Query filter uses raw `police_station__iexact`) | PASS (Security intact; PS filter drops variants) | POT-JUR-001 |
| **K. Tracking Sessions** | YES (`SessionJourneyView`) | YES (`filter_by_jurisdiction`) | PASS (Session ID strictly scoped) | PASS |
| **L. Telemetry Ingestion** | NO (`IngestLocationView`, `BatchIngestLocationView`) | NO (No ownership or jurisdiction check) | FAIL (Any user can inject GPS to any session) | BUG-JUR-001 |
| **M. Telemetry Control** | NO (`StartTrackingView`, `StopTrackingView`, `ProcessionEventIngestView`) | NO (Missing idol jurisdiction checks; Super Admin blocked) | FAIL (Cross-PS start/stop/lifecycle tampering) | BUG-JUR-001, BUG-JUR-004 |
| **N. Mobile Compat Routes** | NO (`MobileSessionView`, `MobileLocationView`) | NO (`permission_classes = []`, auto-assignment fallback) | FAIL (Unauthenticated access & auto-assignment) | BUG-JUR-002 |
| **O. Holding Points** | YES (`filter_by_jurisdiction`) | PARTIAL (`apply_idol_filters` uses raw `police_station__iexact`) | PASS (Security intact; PS filter drops variants) | POT-JUR-001 |
| **P. Dashboard Stats** | YES (`filter_by_jurisdiction`) | PARTIAL (`apply_idol_filters` uses raw `police_station__iexact`) | PASS (Security intact; PS filter drops variants) | POT-JUR-001 |
| **Q. Visarjan Points** | YES (`filter_by_jurisdiction`) | YES (`apply_idol_filters`) | PASS (Enforces server-side jurisdiction) | PASS |
| **R. Police Stations API** | YES (`PoliceStationListView`) | YES (`zone_filter_q`, `ps_filter_q`) | PASS (Non-global users strictly scoped) | PASS |
| **S. Excel Export** | YES (`AssignmentExportExcelView`) | YES (`filter_by_jurisdiction`, `ps_filter_q`, `zone_filter_q`) | PASS (Strictly scoped) | PASS |

---

## 4. Role Matrix

| Role | Expected Jurisdiction | Actual Implementation | Status |
|---|---|---|---|
| **SUPER_ADMIN** | Global Citywide access to all data, management, and operational controls. | Full citywide access in `filter_by_jurisdiction` and `check_user_jurisdiction_over_idol`. Blocked in `StartTrackingView` and `HandoverAssignmentView` due to hardcoded role lists. | PARTIAL (Fix in Start/Handover needed) |
| **SYS_ADMIN** | Zonal System Admin. Strictly restricted to assigned zone. Cannot view or modify data outside zone. | Strictly scoped in `filter_by_jurisdiction` (`zone_filter_q`), `UserCreateUpdateSerializer`, and `EndAssignmentView`. Blocked in `StartTrackingView` and `HandoverAssignmentView`. | PARTIAL (Fix in Start/Handover needed) |
| **MAIN_OFFICER** | Citywide operational officer (or zone-scoped if assigned a specific zone). | Full citywide access (or zonal fallback) in `filter_by_jurisdiction` and `check_user_jurisdiction_over_idol`. Permitted in End Assignment. | PASS |
| **ACP** | Senior Officer scoped to authorized Zone (or Division). | Scoped to Zone/Division in `filter_by_jurisdiction` and `check_user_jurisdiction_over_idol`. Missing cross-jurisdiction check in `StartTrackingView` and `HandoverAssignmentView`. | PARTIAL (Fix in Start/Handover needed) |
| **SHO** | Station House Officer scoped strictly to authorized Police Station (and matching Zone). | Scoped via `ps_filter_q` in `filter_by_jurisdiction`, `CreateAssignmentSerializer`, and `EndAssignmentView`. Missing cross-station check in `StartTrackingView` and `HandoverAssignmentView`. | PARTIAL (Fix in Start/Handover needed) |
| **CONSTABLE** | Ground Staff scoped strictly to own assigned GPID/duty. Cannot manage assignments or view others' data. | Scoped to assigned idol in `filter_by_jurisdiction`. Blocked in assignment creation and ending. Missing ownership check on telemetry ingestion (`IngestLocationView`, `StopTrackingView`, `ProcessionEventIngestView`). | FAIL (Telemetry endpoints need caller check) |

---

## 5. Rajendra Nagar Findings

### Authoritative Reference Data
- **Zone**: `Rajendra Nagar` (Authoritative master representation with space). Secondary legacy data stores `'Rajendranagar'`.
- **Constituent Police Stations (10 Stations)**:
  1. `Attapur`
  2. `Bahadurpura`
  3. `Bandlaguda`
  4. `Chandrayangutta`
  5. `Falaknuma`
  6. `Kalapathar`
  7. `Kamatipura`
  8. `Kanchanbagh`
  9. `Mailardevpally`
  10. `Rajendranagar` (Authoritative PS code `RJNR`).

### Residual Friction Points
1. **Station Name Conflict**: The 10th police station is named `Rajendranagar` in `Idol` and `PoliceStationBoundary`, while its parent zone is `Rajendra Nagar`.
2. **User Account Creation**: `UserCreateUpdateSerializer` line 310, 325, 340 fails when an administrator enters `'Rajendra Nagar'` for police station because it checks `PoliceStationBoundary.objects.filter(ps_name__iexact=police_station)`.
3. **Query Filters**: `apply_idol_filters` and `ActiveTrackingListView` drop Rajendranagar records if a user passes `?police_station=Rajendra Nagar`.

---

## 6. Cross-Zone Findings

The canonical normalization logic in `common/zones.py` is **NOT** Rajendra-Nagar-specific. It covers all seven zones:
- `Charminar`
- `Golconda`
- `Jubilee Hills`
- `Khairatabad`
- `Rajendra Nagar`
- `Secunderabad`
- `Shamshabad`

### Other Zones Affected by Police Station Spelling Variants
The database analysis confirmed spelling/spacing mismatches across secondary tables in other zones as well:
- **Charminar Zone**: `Bhavani Nagar` (in `Idol`) vs `Bhavaninagar` (in `PoliceStationBoundary`), and `Rein Bazar` vs `Reinbazar`.
- **Golconda Zone**: `Langer House` (in `Idol`) vs `Langar House` (in `PoliceStationBoundary`), and `Medipatnam` vs `Mehdipatnam`.

Any view currently using raw `police_station__iexact` (Dashboard, Live Map, Reports, and Users) exhibits the same failure mode in Charminar and Golconda as it does in Rajendra Nagar.

---

## 7. Raw Jurisdiction Comparisons

| File & Line | Code Expression | Classification | Analysis |
|---|---|---|---|
| `apps/tracking/views.py:654` | `qs.filter(assignment__idol__police_station__iexact=ps)` | Potentially Unsafe | Drops variant station names (`Rajendra Nagar`, `Bhavani Nagar`, `Langar House`) on Live Map |
| `apps/idols/views.py:151` | `qs.filter(police_station__iexact=ps)` | Potentially Unsafe | Drops variant station names on Dashboard, Holding Points, and Idol List |
| `apps/reports/views.py:85` | `filtered_qs.filter(police_station__iexact=ps.strip())` | Potentially Unsafe | Drops variant station names on Reports Page |
| `apps/accounts/views.py:83` | `qs.filter(police_station__iexact=police_station.strip())` | Potentially Unsafe | Drops variant station names on User Management list filter |
| `apps/accounts/serializers.py:310` | `PoliceStationBoundary.objects.filter(ps_name__iexact=police_station).first()` | Confirmed Bug | Blocks creating/updating Constable accounts with spaced station names |
| `apps/accounts/serializers.py:325` | `PoliceStationBoundary.objects.filter(ps_name__iexact=police_station).first()` | Confirmed Bug | Blocks creating Constable accounts with spaced station names |
| `apps/accounts/serializers.py:340` | `PoliceStationBoundary.objects.filter(ps_name__iexact=police_station).first()` | Confirmed Bug | Blocks creating SHO accounts with spaced station names |
| `apps/accounts/serializers.py:285` | `normalize_zone(attrs['zone']).lower() != canonical_caller_zone.lower()` | Safe | Canonical strings are normalized before comparison |
| `apps/tracking/views.py:93` | `request.user.role not in ['MAIN_OFFICER', 'ACP', 'SHO']` | Confirmed Bug | Blocks `SUPER_ADMIN`/`SYS_ADMIN` and omits idol jurisdiction validation |
| `apps/assignments/views.py:84` | `request.user.role not in ['MAIN_OFFICER', 'ACP', 'SHO']` | Confirmed Bug | Blocks `SUPER_ADMIN`/`SYS_ADMIN` and omits idol jurisdiction validation |

---

## 8. Security / BYPASS Findings

| Endpoint | Method | Parameter | Vulnerability Description | Severity | Risk Level |
|---|---|---|---|---|---|
| `/api/tracking/session` | `POST` | None (Public) | Unauthenticated route automatically assigns idols to constables and creates tracking sessions | CRITICAL | HIGH RISK |
| `/api/tracking/location` | `POST` | None (Public) | Unauthenticated route allows arbitrary GPS coordinate ingestion | CRITICAL | HIGH RISK |
| `/api/v1/tracking/location/` | `POST` | `session_id` | Any authenticated user can inject GPS coordinates into any session across the city | CRITICAL | HIGH RISK |
| `/api/v1/tracking/location/batch/` | `POST` | `session_id` | Any authenticated user can batch-inject GPS coordinates into any session across the city | CRITICAL | HIGH RISK |
| `/api/v1/tracking/stop/` | `POST` | `session_id` / `gpid` | Any authenticated user can terminate active tracking and force lifecycle transition | CRITICAL | HIGH RISK |
| `/api/v1/tracking/events/` | `POST` | `gpid` | Any authenticated user can force state transitions (`IMMERSION_COMPLETED`, `HOLDING`, etc.) on any GPID | CRITICAL | HIGH RISK |
| `/api/v1/assignments/<id>/handover/` | `POST` | `pk`, `new_constable_id` | Any station officer can reassign idols outside their jurisdiction; target constable is unvalidated | HIGH | MEDIUM RISK |
| `/api/v1/tracking/start/` | `POST` | `assignment_id` | Any station officer can start tracking for idols outside their jurisdiction | HIGH | MEDIUM RISK |

---

## 9. Recommended Fix Order

### 1. CRITICAL (Immediate Hotfix)
1. **Fix BUG-JUR-001 (Telemetry & Lifecycle Ingestion Authorization)**:
   - In `apps/tracking/views.py` (`IngestLocationView`, `BatchIngestLocationView`, `StopTrackingView`, `ProcessionEventIngestView`):
   - Enforce that `request.user == session.assignment.constable`, OR `check_user_jurisdiction_over_idol(request.user, idol)[0] == True`.
2. **Fix BUG-JUR-002 (Lock Down Android Compatibility Routes)**:
   - In `backend/config/urls.py` and `apps/tracking/views.py` (`MobileSessionView`, `MobileLocationView`):
   - Set `permission_classes = [IsAuthenticated]`. Remove `Idol.objects.first()` auto-assignment fallback in production.

### 2. HIGH (Next Priority)
3. **Fix BUG-JUR-003 (Duty Handover RBAC & Jurisdiction)**:
   - In `HandoverAssignmentView`: allow `SUPER_ADMIN` and `SYS_ADMIN`; enforce `check_user_jurisdiction_over_idol(request.user, assignment.idol)`.
   - In `HandoverSerializer`: validate that `new_constable` is active, has `role == CONSTABLE`, and matches `are_same_ps` and `are_same_zone`.
4. **Fix BUG-JUR-004 (Start Tracking Jurisdiction & Role Access)**:
   - In `StartTrackingView`: permit `SUPER_ADMIN` and `SYS_ADMIN`; enforce `check_user_jurisdiction_over_idol(request.user, assignment.idol)` when caller is not the assigned constable.
5. **Fix BUG-JUR-005 (User Management Police Station Validation)**:
   - In `UserCreateUpdateSerializer`: replace `PoliceStationBoundary.objects.filter(ps_name__iexact=police_station)` with `ps_filter_q('ps_name', police_station)`.

### 3. MEDIUM (Operational Consistency)
6. **Fix POT-JUR-001 (Unified PS Filtering Across 4 Views)**:
   - Replace raw `police_station__iexact` with `ps_filter_q` in `apply_idol_filters`, `ActiveTrackingListView`, `CompletedReportsRegistryView`, and `UserListCreateView`.
7. **Fix POT-JUR-002 (Constable Boundary Model Handling)**:
   - In `common/permissions.py:filter_by_jurisdiction`, add explicit handling for `PoliceStationBoundary` model when caller is a `CONSTABLE`.

### 4. LOW (Technical Debt)
8. **Clean up legacy utility comparison helpers** in unused test mock scripts.

---

## 10. No-Change Areas

The following core areas were inspected and verified to be robust, secure, and fully aligned with centralized rules:
1. **Assignment Creation (`CreateAssignmentView` & `CreateAssignmentSerializer`)**: Verified using `check_user_jurisdiction_over_idol`, `are_same_ps`, and `are_same_zone`.
2. **End Assignment (`EndAssignmentView`)**: Verified enforcing `check_user_jurisdiction_over_idol` and restricting force-end tracking privileges to authorized admins (`SUPER_ADMIN`, `MAIN_OFFICER`, `SYS_ADMIN`, superuser).
3. **Assignment Registry (`AssignableIdolRegistryView`)**: Server-side jurisdiction scoping via `filter_by_jurisdiction` and canonical filtering via `ps_filter_q` and `zone_filter_q`.
4. **Officer Eligibility (`AssignableEligibleOfficersView`)**: Scoped to idol jurisdiction with dual `ps_filter_q` and `zone_filter_q`.
5. **Report Downloads (`DownloadIdolReportView`)**: Strictly scoped by `get_object_or_404(filter_by_jurisdiction(Idol.objects.all(), request.user), gpid__iexact=gpid)`.
6. **Session Breadcrumb Retrieval (`SessionJourneyView` & `JourneyView`)**: Enforces jurisdiction scoping; impossible to query telemetry of cross-jurisdiction idols.
7. **Single Idol Inspection (`IdolDetailView`)**: Enforces `filter_by_jurisdiction` lookup; returns 404 for unauthorized GPIDs.
8. **Police Station Directory (`PoliceStationListView`)**: Automatically filters boundaries for non-global officers using `zone_filter_q` and `ps_filter_q`.
9. **User Deletion & Disabling (`UserDeleteView` & `UserToggleActiveView`)**: Enforces `filter_by_jurisdiction(User.objects.all(), request.user)` and prevents self-deletion or unauthorized admin account modification.
10. **Excel Export (`AssignmentExportExcelView`)**: Properly filtered by `filter_by_jurisdiction` and canonical filters.
