# Android API Contract

Every backend endpoint the Android app depends on, with its actual verification
status against the Django repository (`backend/apps/*/urls.py`, audited directly
while building this app — not assumed). Endpoint path constants live in one
place: `data/remote/ApiEndpoints.kt`.

**Re-audited 2026-09-23**, against the backend as it stands after a second round
of parallel changes (`apps/idols/*`, `apps/tracking/*` — see `git status`).

**Integration-hardening pass, same date:** every mismatch the re-audit found
between this app's DTOs/repositories and the confirmed backend contract below
has now been fixed in `dev`/`staging`/`prod` flavors' code paths — see the
per-endpoint sections and the "Tracking DTO field mapping" table for exactly
what changed. This did **not** touch Django, the React frontend, or implement
the still-fictional procession API — see "Procession lifecycle" below.

**🆕 Product-decision change, same date: the 50-meter proximity-to-idol-origin
requirement has been removed from Start Procession entirely.** This was a
deliberate change, not a bug fix. See "Start Procession has no proximity
requirement" immediately below `POST /tracking/start/` for the full
before/after.

Legend:
- ✅ **CONFIRMED AND IMPLEMENTED** — verified against `backend/apps/*/urls.py`
  and the matching view, and this app's real (`dev`/`staging`/`prod`) DTOs/
  repositories now match that contract field-for-field.
- 🚧 **CONCEPTUAL / NOT IMPLEMENTED** — no such endpoint exists on the backend.
  The app calls it anyway through `AppEnvironment.PRODUCTION`/`DEVELOPMENT`/`STAGING`
  flavors, and will get a 404 until the backend implements it.
  `AppEnvironment.MOCK` never calls it — see `data/mock/`. Per explicit
  instruction, this app does **not** invent a real implementation for these.

---

## Authentication

### ✅ `POST /api/v1/auth/login/`
**Status:** CONFIRMED — `apps/accounts/views.py::LoginView`, `AllowAny`.
**Auth:** none (this is how a session begins).
**Request:** `{ "username": string, "password": string }`
**Response 200:** `{ id, username, role, police_id, zone, division, police_station, must_change_password }`
**Errors:** 400 (missing fields), 401 (bad credentials), 403 (account disabled).
**Offline behavior:** requires network; no offline login.
**Idempotency:** N/A.
**Auth mechanism:** Django session cookie (`sessionid`), **not** a token/JWT — confirmed
via `REST_FRAMEWORK.DEFAULT_AUTHENTICATION_CLASSES = [SessionAuthentication, BasicAuthentication]`
in `config/settings/base.py`. `core/auth/SessionCookieJar.kt` persists this encrypted
on-device across process death.

### ✅ `POST /api/v1/auth/logout/`
**Status:** CONFIRMED — `LogoutView`, `IsAuthenticated`.
**Request:** none. **Response 200:** `{ message }`.
**✅ RESOLVED (previously a known gap):** `CSRF_TRUSTED_ORIGINS` is now set in
`config/settings/base.py` — it reads `CSRF_TRUSTED_ORIGINS` from the environment,
falling back to a default list that includes `http://localhost:5173`,
`http://localhost:3000`, their `127.0.0.1` equivalents, and the dev EC2 host
(`http://15.206.58.226`). This previously rejected every authenticated POST
(logout included) with `403 "Origin checking failed"` — re-verified directly
against the current settings file, this is fixed. The app's best-effort logout
(`AuthRepositoryImpl.logout()` clears local session state regardless of the
network result) remains reasonable defensive behavior but is no longer masking
a live bug for this endpoint specifically.
**⚠️ Residual risk:** the fallback list is host-specific (a fixed EC2 IP, not a
domain) — if the dev backend's IP or a future staging/prod origin changes, this
list needs a matching update (or a `CSRF_TRUSTED_ORIGINS` env var set on that
deployment). Worth a quick check against whatever host a `dev`/`staging`/`prod`
flavor actually targets before relying on it.

### ✅ `GET /api/v1/auth/me/`
**Status:** CONFIRMED — `CurrentUserView`, `IsAuthenticated`. Same response shape as login.
**Offline behavior:** on failure, treated as unauthenticated (routes to Login).

---

## Assignment

### ✅🆕 `GET /api/v1/assignments/current/` — the dedicated "my active assignment" endpoint
**Status:** CONFIRMED — `apps/assignments/views.py::CurrentAssignmentView`,
`IsAuthenticated`. **This did not exist on the previous audit pass; it exists now.**
It resolves the TODO-BACKEND gap below directly: no pagination, no client-side
filtering, scoped server-side to `request.user` via
`Assignment.objects.filter(constable=request.user, is_active=True).first()`.
**Response 200:**
```json
{ "active_assignment": {
    "assignment_id": int, "gpid": string, "idol_id": int, "name": string,
    "association_name": string, "police_station": string, "zone": string,
    "procession_state": string, "started_at": string
  } | null
}
```
Note the response shape is a flat, denormalized object — **not** the same shape
as `AssignmentDto` (no `idol_gpid`/`constable` keys; `idol` fields are inlined
under different names, and it includes `procession_state`, which `AssignmentDto`
doesn't have at all).

**✅ IMPLEMENTED (integration-hardening pass, 2026-09-23):**
`AssignmentRepositoryImpl.getActiveAssignment()` now calls
`assignmentApi.currentAssignment()` directly — the old "fetch page 1 of
`GET /assignments/`, pick `is_active=true`" workaround is gone (it could
silently miss an officer's active assignment if it wasn't on page 1). New DTOs:
`CurrentAssignmentResponseDto`/`CurrentAssignmentDto`
(`data/remote/dto/AssignmentDto.kt`). One field could not be carried over
honestly: `Assignment.officerId` is now nullable and is `null` when sourced
from this endpoint, because `current/`'s response never repeats the caller's
own id (it's inherently "my own assignment") — nothing downstream reads this
field today, so leaving it `null` rather than fabricating a value was the
correct call, not a compromise.

### ✅ `GET /api/v1/assignments/` (list — still used elsewhere, e.g. station-officer views)
**Status:** CONFIRMED — `AssignmentListView`. Jurisdiction-filtered server-side
(`common/permissions.py`) — a CONSTABLE only ever sees their own rows via an
explicit `constable=self.request.user` filter (not just the general jurisdiction
filter). Still the right endpoint for anything that needs assignment *history*,
just no longer the only option for "my current one."
**Response:** paginated `{ count, next, previous, results: AssignmentDto[] }`.

### ✅ `GET /api/v1/idols/{gpid}/`
**Status:** CONFIRMED — `IdolDetailView`. Returns `IdolDetailSerializer` fields.

**Update:** when this contract was first written, `Idol` had no origin
coordinate at all. The backend was extended (`apps/idols/models.py`,
`apps/idols/serializers.py`) **while this app was being built**, and now
returns real geocoded fields — re-confirmed directly against the serializer,
not assumed:
- `latitude` / `longitude` — `DecimalField`s, rendered by DRF as JSON
  **strings** (not bare numbers); `IdolDto` relies on `Json { isLenient = true }`
  to parse them into `Double`.
- `geocoding_confidence`, `geocoding_status`, `resolved_address`,
  `geocoding_result_type`.
- `start_gate_eligible` (bool) — `true` only when `geocoding_confidence` is
  `EXACT`/`HIGH` *and* both coordinates are present. **🆕 No longer used as a
  client-side gate (2026-09-23 product decision):** this app still parses it
  (`IdolDto.startGateEligible` → `Idol.startGateEligible`) but
  `ValidateProcessionStartUseCase` doesn't read it, `latitude`, or `longitude`
  at all anymore — see "Start Procession has no proximity requirement" below.
  If the backend still exposes this field, it is not reinterpreted as any kind
  of distance requirement here.
- `height_classification` (`GREEN`/`YELLOW`/`RED`/`SUBTHRESHOLD`/`UNKNOWN`) and
  `is_operational_eligible` (bool) — the backend now computes these itself
  (`IdolDetailSerializer.get_height_classification`/`get_is_operational_eligible`).
  `HeightClass.fromBackendValue()` prefers this over the app's own
  height-feet-based fallback, per spec section 10.

**Remaining gap (now largely moot on the Android side):** there was previously
no confirmed contract for what happens when `start_gate_eligible` is `false`
but an officer needs to start anyway — since this app no longer gates Start
Procession on it at all, that question now belongs entirely to whatever the
backend itself still enforces on `POST /tracking/start/`, not to this app.

**✅ IMPLEMENTED (integration-hardening pass, 2026-09-23):** `IdolDetailSerializer`
also returns `procession_state` (`NOT_STARTED` / `TRACKING` / `MOVING` /
`HOLDING` / `AT_VISARJAN` / `IMMERSION_COMPLETED` — the backend's own
authoritative state, defined on the `Idol` model itself, not a separate
procession app). `IdolDto.kt` now declares and parses this field, mapped onto
`Idol.backendProcessionState: BackendProcessionState`
(`domain/model/BackendProcessionState.kt` — a deliberately **separate** enum
from this app's client-side `ProcessionState`, not a reuse of that name). It is
currently informational only — not wired into `ProcessionStateMachine` or any
UI gating decision — see "Procession lifecycle" below for exactly why a naive
1:1 mapping onto this app's 9-state machine would be wrong.

---

## Tracking (GPS session + telemetry)

### ✅🆕 `POST /api/v1/tracking/start/` — now the real, tested, server-side 50m gate
**Status:** CONFIRMED, and **substantially more built-out than the previous audit
found.** `StartTrackingView` now implements the exact "authoritative 50-meter
start gate" behavior this app's conceptual `/processions/start/` was speculating
about — re-confirmed directly against `apps/tracking/views.py` and its dedicated
test class `TrackingAPITests` (`apps/tracking/tests.py`), which exercises the
full boundary matrix (~30m allowed, ~61m rejected, MEDIUM-confidence rejected,
UNRESOLVED rejected) server-side.

**Real request** (`StartTrackingSerializer`): `assignment_id` (int) **or** `gpid`
(string) — either identifies the assignment — plus optional `device_info`
(string) and optional `latitude`/`longitude` (decimal, the **officer's current
position**).

**Gate logic, in order:**
1. `geocoding_confidence == UNRESOLVED` or missing lat/lon on the idol → `400`,
   `{ error, geocoding_confidence, start_gate_eligible: false }`.
2. `geocoding_confidence == MEDIUM` → `400` (same shape) — a locality-level
   geocode is never trusted for the 50m gate, regardless of how close the
   officer claims to be.
3. `EXACT`/`HIGH` confidence **and** the request included `latitude`/`longitude`
   → server computes Haversine distance against the idol's authoritative
   `latitude`/`longitude`; `> 50.0m` → `400`,
   `{ error, distance_meters, max_allowed_meters: 50.0, geocoding_confidence, start_gate_eligible: true }`.
4. Otherwise → creates a `TrackingSession`, flips `Idol.procession_state` from
   `NOT_STARTED` to `TRACKING` if it was still `NOT_STARTED`, logs a
   `TRACKING_STARTED` `IdolEvent`, returns `201` with `TrackingSessionSerializer`.

**⚠️ Important, previously-unverified detail:** the 50m distance check **only
runs if the request includes `latitude`/`longitude`.** If a caller omits them,
step 3 is skipped entirely and the request succeeds on geocoding-confidence
alone — the server has no independent way to check officer proximity without
being given a position. **This means the Android app must always send its own
fresh GPS fix on every start call** for the server-side check (spec section 3's
"backend validates again" requirement) to actually happen; sending none does
not fail closed, it fails *open*. This is a real characteristic of the deployed
contract, not a hypothetical — worth keeping in mind for whoever wires up the
real integration.

**Response 201** (`TrackingSessionSerializer`): `id`, `assignment`, `gpid`,
`idol_name`, `police_station`, `constable_name`, `constable_username`,
`device_info`, `started_at`, `ended_at`, `status`, `created_at`. This **is** the
server-generated session id the app must treat as authoritative.

**✅ IMPLEMENTED (integration-hardening pass, 2026-09-23):**
`StartTrackingRequestDto`/`StartTrackingResponseDto`
(`data/remote/dto/TrackingDto.kt`) now match this field-for-field — see the
"Tracking DTO field mapping" table below for the full before/after.
`TrackingRepository.startSession()` now takes `officerLocation`/
`officerAccuracyMeters`/`deviceInfo` and is the **sole** real network call for
"start procession" — `AssignmentViewModel.startProcession()` no longer calls
the conceptual `/processions/start/` first; see "Procession lifecycle" below

### 🆕 Start Procession has no proximity requirement (product decision, 2026-09-23)

**This section describes what changed on the Android side only.** The
"Gate logic" described above is the backend's own behavior as last confirmed
during the 2026-09-23 integration-hardening pass — Android did not modify
Django and has not re-verified whether that logic is still exactly as
described; whatever the backend currently enforces on this endpoint is out of
this app's hands entirely.

**What Android used to do:** `ValidateProcessionStartUseCase` computed a
Haversine distance between the officer's GPS fix and `Idol.originLocation`,
and refused to enable the "START PROCESSION" button unless that distance was
`<= 50m` *and* `Idol.startGateEligible` was `true`. This was a **client-side
UX pre-check**, separate from (but designed to mirror) whatever the backend
enforced.

**What Android does now:** that pre-check is gone entirely.
`ValidateProcessionStartUseCase` no longer accepts an idol origin coordinate
as a parameter at all — there is nothing left in its signature that could
express a distance requirement, by construction, not just by omission of a
check. The only client-side pre-conditions before "START PROCESSION" becomes
enabled are:
1. An active assignment (`AssignmentStatus.ACTIVE`).
2. A fresh GPS fix with valid, in-range coordinates.
3. GPS accuracy within `AppConfig.gpsAccuracyThresholdMeters` (30m default) —
   this is a **signal-quality** check, not a proximity-to-idol check, and is
   retained (see "GPS accuracy validation retained" below).

Tapping "START PROCESSION" always sends whatever fresh GPS fix the app has —
regardless of how far it is from `Idol.originLocation` — to
`POST /tracking/start/`, and the officer sees whatever the backend's response
actually says (accepted, or its real rejection message). Android does not
predict, replicate, or second-guess that decision.

`Idol.originLocation`/`Idol.originAddress` remain in the domain model as
**reference/display data only** (e.g. the "FROM" line on `AssignmentCard`) —
never read by the start flow. `Idol.startGateEligible` is still parsed from
the backend but is not read by the start flow either; if the backend still
returns it, this app does not reinterpret it as a proximity requirement.

**GPS accuracy validation retained:** `GpsQualityValidator` (rejecting
NaN/zero/negative/`>200m`-accuracy fixes before they're even persisted to
Room) and `ValidateProcessionStartUseCase`'s `GpsAccuracyTooLow` check are
both unrelated to the removed proximity rule — they validate the GPS
*signal's own quality*, not distance to anything, and were kept.
`Haversine.distanceMeters()` itself was also kept — `GpsQualityValidator`
still uses it to detect near-duplicate consecutive GPS fixes (a legitimate,
separate use, unrelated to idol-origin distance) — but the idol-origin
distance calculation that used to run inside `ValidateProcessionStartUseCase`
was removed along with the rule it existed for.
for how the client-side 9-state timeline still advances without that call.

### ✅ `POST /api/v1/tracking/location/` (single-point ingest)
**Status:** CONFIRMED — `IngestLocationView`. Real request: `session_id` (int),
`latitude`/`longitude` (float), optional `accuracy`/`speed`/`heading` (float),
`recorded_at` (required, ISO datetime). Dedupes by `(session, recorded_at)` via
`get_or_create`. **🆕 Also auto-derives procession state from speed** — see
"Procession lifecycle" below; this is new, confirmed behavior, not something
previously documented.

### ✅ `POST /api/v1/tracking/location/batch/`
**Status:** CONFIRMED — `BatchIngestLocationView`. Deduplicates by
`(session, recorded_at)` server-side (re-verified via
`test_batch_location_ingestion_with_deduplication`, which posts the same batch
twice and asserts the second call inserts 0 / skips all as duplicates — this is
real, tested idempotency, not a documentation claim).

**✅ IMPLEMENTED (integration-hardening pass, 2026-09-23):**
`TelemetryBatchRequestDto`/`TelemetryPointDto`/`TelemetryBatchResponseDto`
(`data/remote/dto/TrackingDto.kt`) now match `BatchIngestLocationSerializer`
and the view body field-for-field — see the "Tracking DTO field mapping" table
below. One thing this fix could **not** resolve, because it's a real, confirmed
gap in the backend itself, not an Android-side naming bug: the backend does not
read `client_event_id` at all, so true idempotency against a retried point that
ends up with a *different* `recorded_at` is still not guaranteed server-side —
this app still sends the field (harmless, forward-compatible) but does not rely
on it.

### ✅ `POST /api/v1/tracking/stop/`
**Status:** CONFIRMED — `StopTrackingView`. Real request (plain `request.data`,
no serializer): `session_id` **or** `gpid`, optional `final_state`
(`AT_VISARJAN` / `IMMERSION_COMPLETED`). Response includes `procession_state`
after the update.
**✅ IMPLEMENTED (integration-hardening pass, 2026-09-23):**
`StopTrackingRequestDto` (`data/remote/dto/TrackingDto.kt`) now sends
`session_id` (was `tracking_session_id`) and no longer sends `stopped_at` (the
backend has no such field — it doesn't record when the stop request arrived,
only `ended_at` via `session.stop_session()`). The real, optional `final_state`
field is now modeled too, but `TrackingRepositoryImpl.finalizeStopIfReady()`
still always sends `null` for it — this app does not yet decide when a stop
corresponds to `AT_VISARJAN` vs `IMMERSION_COMPLETED` (see "Procession
lifecycle" below); adding that decision was explicitly out of scope for this
pass ("do not add new product features").

### ✅🆕 `GET /api/v1/tracking/idols/{gpid}/latest/` — previously-documented bug is now fixed
**Status:** CONFIRMED and **working** — re-read `LatestLocationView.get()`
directly: it now ends with `return Response({...})`. The previous audit found
this endpoint built its response and never returned it (falling through to an
implicit `None` → a 500). **That bug is gone.** Confirmed further by a new
backend regression test specifically guarding against a regression of this
exact bug: `AndroidAPKIntegrationTests.test_latest_location_returns_200_and_payload`
(`apps/tracking/tests.py`), whose docstring literally says "Regression test for
`LatestLocationView.get()` returning proper DRF Response." This app still does
not call it (no functional need arose), but it is no longer something to avoid —
it's a normal, working, tested endpoint now.

### Tracking DTO field mapping (as requested by the integration-hardening audit)

Every field on every tracking DTO, re-verified against the real serializer/view
and now matching exactly. "Mapper" is the Kotlin file that constructs or reads
the DTO.

| Android field | Backend field | Request/response | Mapper | Status |
|---|---|---|---|---|
| `StartTrackingRequestDto.assignmentId` | `assignment_id` | request | `TrackingRepositoryImpl.startSession()` | confirmed |
| `StartTrackingRequestDto.gpid` | `gpid` | request | `TrackingRepositoryImpl.startSession()` | confirmed |
| `StartTrackingRequestDto.latitude` | `latitude` | request | `TrackingRepositoryImpl.startSession()` | confirmed (added — was missing) |
| `StartTrackingRequestDto.longitude` | `longitude` | request | `TrackingRepositoryImpl.startSession()` | confirmed (added — was missing) |
| `StartTrackingRequestDto.deviceInfo` | `device_info` | request | `TrackingRepositoryImpl.startSession()` | confirmed (added — was missing) |
| `StartTrackingResponseDto.id` | `id` | response | `TrackingRepositoryImpl.startSession()` | confirmed (was `trackingSessionId`/`tracking_session_id` — never matched) |
| `StartTrackingResponseDto.assignment` | `assignment` | response | *(parsed, currently unused)* | confirmed |
| `StartTrackingResponseDto.gpid` | `gpid` | response | `TrackingRepositoryImpl.startSession()` | confirmed |
| `StartTrackingResponseDto.idolName` | `idol_name` | response | *(parsed, currently unused)* | confirmed |
| `StartTrackingResponseDto.policeStation` | `police_station` | response | *(parsed, currently unused)* | confirmed |
| `StartTrackingResponseDto.constableName` | `constable_name` | response | *(parsed, currently unused)* | confirmed |
| `StartTrackingResponseDto.constableUsername` | `constable_username` | response | *(parsed, currently unused)* | confirmed |
| `StartTrackingResponseDto.deviceInfo` | `device_info` | response | *(parsed, currently unused)* | confirmed |
| `StartTrackingResponseDto.startedAt` | `started_at` | response | `TrackingRepositoryImpl.startSession()` | confirmed |
| `StartTrackingResponseDto.endedAt` | `ended_at` | response | *(parsed, currently unused)* | confirmed |
| `StartTrackingResponseDto.status` | `status` | response | *(parsed, currently unused)* | confirmed |
| `StartTrackingResponseDto.createdAt` | `created_at` | response | *(parsed, currently unused)* | confirmed |
| `TelemetryBatchRequestDto.sessionId` | `session_id` | request | `TrackingRepositoryImpl.syncPendingTelemetry()` | confirmed (was `tracking_session_id` — never matched) |
| `TelemetryBatchRequestDto.points[]` | `points[]` | request | `TelemetryPointEntity.toDto()` | confirmed |
| `TelemetryPointDto.clientEventId` | *(not read by backend)* | request | `TelemetryPointEntity.toDto()` | sent, not relied upon — see note above |
| `TelemetryPointDto.latitude`/`longitude` | `latitude`/`longitude` | request | `TelemetryPointEntity.toDto()` | confirmed |
| `TelemetryPointDto.accuracy` | `accuracy` | request | `TelemetryPointEntity.toDto()` | confirmed |
| `TelemetryPointDto.altitude` | *(not read by backend)* | request | `TelemetryPointEntity.toDto()` | sent, harmless, backend ignores it |
| `TelemetryPointDto.speed` | `speed` | request | `TelemetryPointEntity.toDto()` | confirmed |
| `TelemetryPointDto.heading` | `heading` | request | `TelemetryPointEntity.toDto()` | confirmed (was `bearing` — never matched) |
| `TelemetryPointDto.recordedAt` | `recorded_at` | request | `TelemetryPointEntity.toDto()` | confirmed |
| `TelemetryBatchResponseDto.status` | `status` | response | *(parsed, currently unused)* | confirmed (added — was missing) |
| `TelemetryBatchResponseDto.received` | `received` | response | *(parsed, currently unused)* | confirmed (added — was missing) |
| `TelemetryBatchResponseDto.inserted` | `inserted` | response | *(parsed, currently unused)* | confirmed (replaces fictional `accepted`) |
| `TelemetryBatchResponseDto.duplicatesSkipped` | `duplicates_skipped` | response | *(parsed, currently unused)* | confirmed (replaces fictional `duplicates`) |
| `StopTrackingRequestDto.sessionId` | `session_id` | request | `TrackingRepositoryImpl.finalizeStopIfReady()` | confirmed (was `tracking_session_id` — never matched) |
| `StopTrackingRequestDto.finalState` | `final_state` | request | `TrackingRepositoryImpl.finalizeStopIfReady()` | confirmed field, always sent `null` today (see note above) — `stopped_at` removed, backend has no such field |
| `CurrentAssignmentResponseDto.activeAssignment` | `active_assignment` | response | `AssignmentRepositoryImpl.getActiveAssignment()` | confirmed |
| `CurrentAssignmentDto.assignmentId`/`gpid`/`idolId`/`policeStation`/`zone`/`processionState`/`startedAt` | `assignment_id`/`gpid`/`idol_id`/`police_station`/`zone`/`procession_state`/`started_at` | response | `AssignmentRepositoryImpl.getActiveAssignment()` | confirmed |
| `IdolDto.processionState` | `procession_state` | response | `AssignmentRepositoryImpl.toDomain()` → `Idol.backendProcessionState` | confirmed (added — was missing) |

---

## Procession lifecycle

**Re-audit finding — this section changed the most.** `apps/processions` still
does not exist as a Django app, and `/api/v1/processions/start/` /
`/api/v1/processions/events/` remain **entirely fictional URLs — kept
conceptual per explicit instruction, not implemented as fake Retrofit calls.**
But it would now be **inaccurate** to describe the backend as having "no
procession lifecycle." It has one — it's just structurally different from what
this app's `ProcessionStateMachine` models, and it was built directly into
`apps/tracking`, not a separate app:

**The real, confirmed backend procession state space** (`Idol.procession_state`,
`apps/idols/models.py::ProcessionState`) has **6** states:
`NOT_STARTED → TRACKING → {MOVING ⇄ HOLDING} → {AT_VISARJAN, IMMERSION_COMPLETED}`

- `NOT_STARTED → TRACKING`: set by `POST /tracking/start/` (see above) — this
  **is** the real "start procession," gated by the 50m rule.
- `TRACKING/HOLDING → MOVING` and `MOVING → HOLDING`: **auto-derived
  server-side from raw telemetry speed**, inside `IngestLocationView` and
  `MobileLocationView` — `speed > 1.0 m/s` flips to `MOVING`, `speed <= 0.3 m/s`
  while `MOVING` flips to `HOLDING`. **There is no client-tapped "I am moving" /
  "I am holding" event on the real backend at all** — the officer's device does
  not decide this state, its GPS does, automatically, as a side effect of
  ordinary telemetry ingestion.
- `→ AT_VISARJAN` / `→ IMMERSION_COMPLETED`: the only two states an explicit
  client call can set, via `final_state` on `POST /tracking/stop/`.

**This app's `ProcessionStateMachine.kt` models 9 states** (`ASSIGNED`,
`AT_IDOL`, `PROCESSION_STARTED`, `MOVING`, `REACHED_VISARJAN_AREA`,
`VISARJAN_DONE`, `HOLDING`, `RETURNING_TO_PANDAL`, `RETURNED_TO_PANDAL`), all
advanced by explicit officer-tapped events synced individually — there is no
backend concept matching `REACHED_VISARJAN_AREA`, `RETURNING_TO_PANDAL`, or
`RETURNED_TO_PANDAL` today, and the backend's `MOVING`/`HOLDING` are automatic
where this app's are event-driven. **Note also a name collision, not just a
missing concept:** this app's `HOLDING` is only reachable *after*
`REACHED_VISARJAN_AREA` (a deliberate pause at the immersion site); the
backend's `HOLDING` is a general "stopped moving" signal reachable at any point
during `MOVING` — same word, different meaning. A future integration must not
assume these line up.

**What this means concretely:** the spec's event-driven procession model (spec
section 44/51, `docs` throughout this repo) is a **product decision this app
was built to anticipate**, not something confirmed to exist on the backend as
designed. The backend's actual, live approach is closer to
"start is a gate, movement is inferred from GPS, only the two terminal states
are explicit" — a simpler design that may turn out to be *the* real target, or
the backend's procession app may still get built later to match this app's
richer model. Until a real decision is made and an actual `apps/processions`
(or equivalent) app ships, `ProcessionDto.kt`'s request/response types stay
exactly as conceptual as before — untouched by the integration-hardening pass,
per the "keep them conceptual, do not implement a real procession API"
instruction.

**✅ IMPLEMENTED (integration-hardening pass, 2026-09-23) — how "start" now
actually works client-side:** `AssignmentViewModel.startProcession()` calls
`TrackingRepository.startSession()` (the real `/tracking/start/` gate) as its
**only** network call for starting a procession. On success, it calls the new
`ProcessionRepository.recordLocalStart()` — a **local-only, no-network** Room
insert, already marked `SYNCED` — so this app's own 9-state timeline UI still
advances to `PROCESSION_STARTED`. There is nothing to sync for that transition
because the real backend call that just succeeded already **is** the
authoritative confirmation; a second network round trip to the fictional
`/processions/start/` would have nothing real to confirm against.
`ProcessionRepository.submitProcessionStart()` (the old conceptual-endpoint
call) is unused by this flow now — left in place, unmodified, as scaffolding
only, exactly as it was, in case a real dedicated procession-start endpoint is
ever built.

### 🚧 `POST /api/v1/processions/start/` — still conceptual, still unimplemented
**Superseded in practice by `POST /api/v1/tracking/start/`** (see above and
immediately above), which already does real, tested, server-side 50m-gated
session creation — and which this app's real "start procession" action now
actually calls. This endpoint constant, DTO, and Retrofit method remain in the
codebase (`ProcessionApi.kt`, `ProcessionDto.kt`) but are not called by any
real user flow.
**Conceptual request (unchanged):** `{ assignment_id, gpid, latitude, longitude, accuracy, occurred_at }`
**Conceptual response (unchanged):** `{ gpid, state, occurred_at }`

### 🚧 `POST /api/v1/processions/events/` — still conceptual
No change from the previous audit: nothing server-side deduplicates by
`client_event_id` or validates transitions against this app's state machine.
The closest real analogue (`/tracking/location/` auto-deriving `MOVING`/
`HOLDING`, and `/tracking/stop/`'s `final_state`) is described above — it is
**not** a drop-in replacement for this endpoint's conceptual contract.
**Conceptual request (unchanged):** `{ client_event_id, assignment_id, gpid, event_type, latitude, longitude, occurred_at }`
**Conceptual response (unchanged):** `{ gpid, state, occurred_at }`

---

## Not used by this app (present in the backend, out of scope here)
- `apps/geography` — no endpoints exposed yet (`urls.py` is empty, "Phase 10").
- `apps/audit` — no endpoints exposed yet.
- `apps/reports` (PDF generation) — dashboard-only, no field-officer use case.
- `apps/tracking` mobile-direct routes (`/api/tracking/session`, `/api/tracking/location`)
  — these exist for the *existing* Android APK referenced in `config/urls.py`
  (`MobileSessionView`/`MobileLocationView`), a different, undocumented client.
  This rebuild intentionally goes through the versioned `/api/v1/tracking/` routes
  instead, since those are the ones with real jurisdiction/auth enforcement.
