# TG Police Visarjan Tracking (Android)

Native Kotlin/Jetpack Compose field-officer app for the Hyderabad City Police
Ganesh Visarjan tracking system. Built as an independent client against the
existing Django backend — see [`../backend`](../backend) and
[`../frontend`](../frontend) (the command dashboard) for the other two pieces
of this system. This app was built in parallel with both, without modifying
either.

## Status

This is the **first milestone**: Login → Active Assignment → Start Procession
(fresh GPS submitted to the backend, no proximity requirement — see
"Known limitations" below) → procession state-machine actions (Moving /
Reached Visarjan Area / Visarjan Done / Holding / Returning / Returned) →
Stop Tracking, running end-to-end in **mock mode** without the Django backend.
Real-backend flavors (`dev`/`staging`/`prod`) are wired up against every
endpoint confirmed to exist, and clearly flagged where the backend contract is
still conceptual — see [`docs/API_CONTRACT.md`](docs/API_CONTRACT.md).

**⚠️ Build verification:** this project was written in an environment with no
JDK, Android SDK, or Gradle installed, so `./gradlew assembleDebug` could not
actually be run here — see "Known limitations" below. It has not been opened in
Android Studio. Before relying on it, open it there and let Gradle sync resolve
any dependency-version mismatch the way real Android tooling would surface.

## Architecture

```
UI (Compose)  →  ViewModel  →  Repository (domain interface)
                                    ├── Room (durable local queue)
                                    ├── Retrofit (remote API)
                                    └── Mock (in-memory, no network)
                                          ↓
                                   WorkManager (deferred sync, backoff)
                                          ↓
                                Foreground Service (GPS collection)
```

- **`core/`** — config (environment/BuildConfig), network (Retrofit/OkHttp
  plumbing, structured `ApiResult`/`ApiError`), auth (session cookie
  persistence, CSRF), logging.
- **`domain/`** — pure Kotlin models and use cases (`ProcessionStateMachine`,
  `Haversine`, `ValidateProcessionStartUseCase`, `GpsQualityValidator`) and
  repository *interfaces*. No Android framework dependencies here — this is
  what the unit tests exercise directly.
- **`data/`** — `local/` (Room), `remote/` (Retrofit APIs + DTOs), `mock/`
  (in-memory fakes), `repository/` (real implementations, DTO↔domain mappers).
- **`location/`** — thin Fused Location Provider wrapper + permission helpers.
- **`service/`** — `LocationTrackingService`, the foreground GPS collector.
- **`worker/`** — `TelemetrySyncWorker`, `ProcessionEventSyncWorker`,
  `SyncScheduler` (the only place WorkManager requests get built).
- **`feature/`** — one package per screen (auth, home, assignment, tracking,
  profile, debug, splash), each a small ViewModel + Composable.
- **`di/`** — Hilt modules. `RepositoryModule` is the single place mock vs.
  real repositories are selected, based on `AppEnvironment.current`.

### Why session cookies, not a token?

The Django backend uses `SessionAuthentication` (see
`config/settings/base.py`), not JWT/OAuth tokens. `SessionCookieJar` persists
the `sessionid`/`csrftoken` cookies encrypted on-device
(`EncryptedSharedPreferences`) so the officer doesn't have to log in every time
the app process is killed. If the backend later adds token auth, only
`core/auth/` and `di/NetworkModule.kt` need to change — nothing above the
repository layer knows how auth works.

### The procession state machine

`domain/usecase/ProcessionStateMachine.kt` is the single source of truth for
which action is legal from which `ProcessionState`. UI, ViewModels, and the
sync workers all route through it rather than re-deriving the rule. The
backend is still the actual authority — every transition request is
independently validated server-side (see API contract) — but this lets the
tracking screen grey out an illegal action before making a network call at
all, and makes the whole workflow exhaustively unit-testable
(`ProcessionStateMachineTest`).

## Setup

- **Android Studio:** Koala (2024.1) or newer.
- **JDK:** 17 (set in `app/build.gradle.kts` `compileOptions`).
- **Gradle:** wrapper included (`./gradlew`), Gradle 8.9 / AGP 8.5.2.
- Open the `android/` folder as the project root in Android Studio and let it
  sync. It will resolve `compileSdk 34` / `minSdk 26` automatically.

## Build variants

Two independent axes: **build type** (`debug`/`release`) × **environment
flavor** (`mock`/`dev`/`staging`/`prod`) — e.g. `mockDebug`, `devDebug`,
`prodRelease`.

| Flavor | `API_BASE_URL` | `USE_MOCK_API` | Use for |
|---|---|---|---|
| `mock` | (unused) | `true` | UI development, demos, this milestone |
| `dev` | `http://15.206.58.226/api/v1/` | `false` | Against the shared dev EC2 backend |
| `staging` | placeholder — set before use | `false` | Pre-prod |
| `prod` | placeholder — set before use | `false` | Production |

**No secrets live in these values** — `API_BASE_URL` is a plain host, not a
credential. Per-developer overrides (e.g. a local backend on your LAN IP)
should go in a gitignored `local.properties`-driven override rather than
editing `build.gradle.kts`; this project doesn't currently need one since the
only "secret-shaped" value here is a public dev IP, not a key.

Run mock mode:
```bash
./gradlew installMockDebug
```

### Business-rule constants

`GPS_ACCURACY_THRESHOLD_METERS` (30), `LOCATION_UPDATE_INTERVAL_MS` (8000),
`TELEMETRY_BATCH_SIZE` (25), etc. are `buildConfigField`s in
`app/build.gradle.kts`, surfaced through `core/config/AppConfig.kt`. These are
**Android-side defaults**, not confirmed backend business rules.
**There is deliberately no `PROCESSION_START_MAX_DISTANCE_METERS`** — the
50-meter proximity-to-idol-origin requirement was removed from the Start
Procession flow entirely (2026-09-23 product decision); see
[`docs/API_CONTRACT.md`](docs/API_CONTRACT.md) "Start Procession has no
proximity requirement" for the full before/after.

## Mock mode

`AppEnvironment.current` resolves from `BuildConfig.USE_MOCK_API` at compile
time (never a runtime toggle a field officer could flip). In mock mode:
- `MockAuthRepository` accepts any non-blank username/password.
- `MockAssignmentRepository` returns one sample assignment
  (`data/mock/MockData.kt`) with a real-looking origin coordinate near
  Charminar — reference/display data only; Start Procession does not measure
  anything against it.
- `MockTrackingRepository`/`MockProcessionRepository` use the **real Room
  database** (Room is local infrastructure, not something worth faking) —
  only the network leg is simulated with a short delay. This means the
  offline-queue and pending-sync-count UI behaves identically to production.

## Permissions

Requested contextually (not at app startup): `ACCESS_FINE_LOCATION` /
`ACCESS_COARSE_LOCATION` when the officer opens the Assignment screen,
`POST_NOTIFICATIONS` and `ACCESS_BACKGROUND_LOCATION` when they tap Start
Procession. Starting a procession additionally requires **precise** location
specifically (`ACCESS_FINE_LOCATION`, not just coarse) — see
`location/LocationPermissions.kt`.

## Tracking architecture

Every accepted GPS fix goes **validate → Room insert → (later) sync attempt.**
Never fix → network POST directly — a failed request must never lose a point.
`LocationTrackingService` is a foreground service (location type) that:
- starts only from an explicit "Start Procession" action (never on boot —
  there is no `BOOT_COMPLETED` receiver in the manifest),
- publishes its state through `TrackingServiceState` (a Hilt singleton
  `StateFlow` holder, not a static var) so it survives Activity recreation,
- does not depend on any Activity remaining alive.

## Offline synchronization

`TelemetrySyncWorker` / `ProcessionEventSyncWorker` run via WorkManager with a
`NetworkType.CONNECTED` constraint and exponential backoff — WorkManager itself
holds/retries the request until connectivity returns, so there's no manual
polling. A 15-minute periodic safety-net worker
(`SyncScheduler.schedulePeriodicSafetyNet()`) covers the case where the app
process is killed with nothing left to trigger a fresh enqueue (spec test
scenario G — network down 30+ minutes). Stopping tracking marks the session
`STOP_REQUESTED` locally (works offline) — `TelemetrySyncWorker` only calls the
backend's stop endpoint once that session's queue is fully drained.

## Testing

```bash
./gradlew test              # domain + repository unit tests (JVM, MockK/Truth)
./gradlew connectedAndroidTest   # Room DAO instrumentation tests (needs a device/emulator)
```

Covered: `Haversine` (general boundary-matrix tests — kept because
`GpsQualityValidator` still uses it for duplicate-fix detection, a use
unrelated to the removed idol-origin distance check), `ProcessionStateMachine`
(every valid transition + representative invalid ones),
`ValidateProcessionStartUseCase` (assignment/GPS-availability/accuracy matrix
— explicitly including a case proving a GPS fix on the other side of the
country is still `Ready`, since there is no distance parameter left to reject
it with), `GpsQualityValidator`, Room DAO chronological-ordering and
dedup-by-`clientEventId` behavior, and sync-engine scenarios (batch upload,
failure-then-retry, chronological-order-preserved-on-partial-failure, a
backend start-request rejection surfaced as an error, and the actual start GPS
fix being persisted locally) against `TrackingRepositoryImpl`/
`ProcessionRepositoryImpl` with the DAOs/API faked via MockK.
`ApiErrorMapperTest` guards the real-backend-error-body extraction fix.
`ServiceRestartDecisionTest` covers the foreground-service restart scenarios
(active session resumed, no session does nothing, a stopped/stop-requested
session does not resume GPS) as pure JVM logic, extracted specifically so this
doesn't need an emulator or Hilt test infra to verify.

Compose UI tests (`app/src/androidTest/`, need a device/emulator) cover
`LoginScreen` (invalid credentials, successful login, blank-field validation),
`AssignmentScreen` (active assignment displayed, no assignment, a GPS fix
~1,500km from the idol's registered origin still allowed to start — the
explicit proof the old 50m rule is gone, no GPS / an invalid-coordinate fix
disabling Start, poor GPS accuracy disabling Start, a real backend success
starting the procession and navigating on, a real backend rejection doing
neither, and no GPID picker/free-text input existing anywhere on the screen),
and `TrackingScreen` (every reachable `ProcessionState` shows the right status
and exactly the actions `ProcessionStateMachine` allows). Each constructs its
ViewModel directly with faked dependencies and passes it into the Composable's
`viewModel` parameter, bypassing `hiltViewModel()` — no Hilt test runner
needed. **Not yet written:** a full ViewModel test suite beyond what these and
the repository-level tests already exercise, and true foreground-service
instrumented tests (would need Hilt test infrastructure not yet set up — see
`ServiceRestartDecisionTest` for what's covered at the JVM level instead).

## Known limitations (read before trusting this build)

*Re-audited 2026-09-23 against the backend's current state, then a focused
integration-hardening pass fixed every DTO/repository mismatch the re-audit
found — see `docs/API_CONTRACT.md` for full per-endpoint detail and the
complete field mapping table.*

- **✅ CHANGED (product decision, 2026-09-23): Start Procession has no
  proximity requirement anymore.** The old client-side check (officer must be
  within 50m of the idol's registered origin, per `ValidateProcessionStartUseCase`
  + `Haversine`) has been removed entirely — not disabled, not hidden, removed
  from the use case's parameters. Start Procession now only requires an active
  assignment and a fresh, valid, sufficiently-accurate GPS fix; that fix is
  always submitted to `POST /tracking/start/` regardless of distance from
  anything idol-related, and the backend's response (accept or its own
  rejection reason) is the only thing that decides the outcome. The idol's
  registered origin (`Idol.originLocation`) is reference/display data only.
  See `docs/API_CONTRACT.md` "Start Procession has no proximity requirement"
  for the full before/after and exactly what was and wasn't touched.
- **Never compiled.** This project was authored in a sandbox with no JDK/SDK/
  Gradle installed — open it in real Android Studio and treat the first sync
  as the actual first build verification. Some dependency versions in
  `gradle/libs.versions.toml` may need a bump if AGP/Studio flags them.
  This integration-hardening pass made only structural/static verification
  (imports resolve, types line up, tests mirror existing conventions) —
  nothing here has been through `javac`/`kotlinc`.
- **Procession lifecycle: still no `apps/processions` Django app, but the real
  backend isn't silent on this anymore.** `POST /api/v1/tracking/start/` is
  now the confirmed, real "start procession" call (folding it into "start
  tracking" rather than a separate endpoint) — `AssignmentViewModel` calls it
  directly with a fresh GPS fix, and it's the only real network call the start
  flow makes. `MOVING`/`HOLDING` are auto-derived server-side from GPS speed
  on every telemetry point — not client-tapped events. Only `AT_VISARJAN` and
  `IMMERSION_COMPLETED` are explicit (via `/tracking/stop/`'s `final_state`,
  which this app doesn't yet decide when to send). This app's 9-state, fully
  event-driven `ProcessionStateMachine` still has no backend equivalent for
  `REACHED_VISARJAN_AREA`, `RETURNING_TO_PANDAL`, or `RETURNED_TO_PANDAL`, and
  its `HOLDING` means something different from the backend's `HOLDING` — see
  "Procession lifecycle" in `docs/API_CONTRACT.md` for the full comparison.
  `ProcessionApi`/`ProcessionDto` remain untouched, conceptual scaffolding,
  unused by any real flow.
- **✅ FIXED: `StartTrackingRequestDto`/`ResponseDto` and the telemetry batch
  DTOs now match the real backend field-for-field** — `latitude`/`longitude`/
  `device_info` added to the start request (required for the 50m gate to
  actually run server-side), `id` instead of the fictional
  `tracking_session_id` on the response, `session_id` instead of
  `tracking_session_id` on the batch/stop requests, `heading` instead of
  `bearing`, and a telemetry-batch response DTO that matches the real
  `{status, received, inserted, duplicates_skipped}` shape instead of a
  fictional `{accepted, duplicates}`. Full table in `docs/API_CONTRACT.md`.
- **✅ FIXED: a real backend business-rule rejection (e.g. the 50m gate's
  `START_GATE_REJECTED` message) now actually reaches the officer.**
  `ApiErrorMapper` previously used Retrofit's generic HTTP status line instead
  of reading the response body — a real bug that had never manifested because
  nothing called `/tracking/start/` with coordinates before this pass. Now
  fixed and unit-tested (`ApiErrorMapperTest`).
- **✅ FIXED: `LocationTrackingService` foreground-service restart.** A
  system-triggered restart with a null `Intent` previously never resumed GPS
  collection or the foreground notification, and could crash the process by
  not calling `startForeground()` promptly. Now resolved by asking Room (the
  authoritative local source, not a static var) whether an ACTIVE session
  exists before deciding to resume or stop — see `ServiceRestartDecision.kt`
  (unit-tested) and `LocationTrackingService.handleNullIntentRestart()`.
- **✅ FIXED: `GET /api/v1/assignments/current/` is now used.**
  `AssignmentRepositoryImpl` calls it directly — the old "fetch page 1 of the
  assignment list, pick `is_active`" workaround (which could silently miss an
  officer's active assignment) is gone.
- **✅ FIXED: `Idol.backendProcessionState` is now parsed** from the backend's
  `procession_state` field, kept in its own `BackendProcessionState` enum
  (deliberately not reusing this app's `ProcessionState` name) — informational
  only today, not wired into any gating decision; see `docs/API_CONTRACT.md`.
- **✅ RESOLVED: `CSRF_TRUSTED_ORIGINS` is now set** in
  `config/settings/base.py` (env-var driven, with a sensible default list
  covering local dev and the dev EC2 host) — re-verified directly against the
  current settings file. Previously every authenticated POST including
  `/auth/logout/` was rejected with `403 Origin checking failed`; that's fixed.
  Worth re-checking the default list covers whatever host a `staging`/`prod`
  flavor eventually targets.
- **✅ RESOLVED: `/tracking/idols/{gpid}/latest/` is no longer broken** —
  `LatestLocationView.get()` now correctly returns its `Response`, and the
  backend has a dedicated regression test guarding against this exact bug
  recurring. This app still doesn't call it (no functional need), but it's a
  normal working endpoint now, not something to avoid.
- **✅ REMOVED: the unused `RECEIVE_BOOT_COMPLETED` manifest permission** —
  there was no `BroadcastReceiver` for it and no boot-triggered tracking
  exists by design.
- **No push/FCM, no offline procession-start.** Starting a procession requires
  network (spec section 51: never invent a server session id), by design.
- Compose UI tests now cover Login (invalid/successful), Assignment (all five
  start-gate states plus active/no assignment), and Tracking (every reachable
  `ProcessionState`) — see `docs/API_CONTRACT.md`-adjacent test files under
  `app/src/androidTest/`. A full ViewModel test suite beyond what these and
  the repository-level tests exercise, and release signing configuration
  (`keystore.properties`, intentionally not created), are still not part of
  this milestone.
