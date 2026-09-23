# TG Police Visarjan Tracker v1.1.0

## Production Release

### What changed since v1.0.0

- **Start Procession has no 50-meter proximity requirement anymore**
  (product decision, 2026-09-23). The old client-side distance check against
  the idol's registered origin has been removed entirely — Start Procession
  now requires only an active assignment and a fresh, sufficiently-accurate
  GPS fix, submitted to the backend regardless of distance from anything
  idol-related. The backend's response is the sole authority on acceptance.
- **"Reached Site" — a new first field milestone.** The officer can now
  explicitly confirm physical arrival at the pandal before starting the
  procession. No backend endpoint exists for this event yet (re-confirmed
  against the current backend); it is recorded locally on-device only, through
  the same architecture already used for this app's other officer-tapped
  events, ready to sync once a real endpoint exists. See
  `docs/API_CONTRACT.md` "Reached Site".
- **Assignment screen shows more of what's already available**: police
  station (newly parsed from the backend), zone, pandal/idol name, and the
  backend's own procession state, alongside the existing GPID/height/address.
- **Invalid-assignment safety net**: if an assignment for an idol below the
  15ft operational threshold is ever returned (the backend's own filter
  should prevent this), the app no longer silently proceeds — it logs a safe
  diagnostic and shows an explicit "Invalid Assignment" state instead of the
  normal Start Procession flow.
- **Native splash screen, updated launcher icon, and login screen artwork** —
  a consistent tracking-pin + temple-tower mark across all three, in the
  app's existing dark/amber theme. No AI-generated police emblem — this is
  original artwork, never presented as an official insignia.
- Continued: real GPS persistence for the actual start location
  (`startLatitude`/`startLongitude`/`startTimestamp`, not just sent to the
  backend and discarded), foreground-service restart recovery, offline
  telemetry queueing via Room + WorkManager, and the rest of the
  architecture carried over unchanged from v1.0.0.

### Features (carried over from v1.0.0)

- Secure officer login
- Current GPID assignment (`GET /api/v1/assignments/current/` — officer is
  never able to pick an arbitrary GPID)
- Live procession tracking
- Continuous GPS tracking via foreground location service
- Offline GPS queue with durable Room storage and WorkManager sync
- Background tracking (GPS continues with the screen off / app backgrounded)
- Telemetry synchronization
- Live backend connectivity
- Procession start/stop workflow
- Professional Telangana Police themed UI (dark charcoal / amber accent)
- Production permission handling

### Backend

Production EC2 API:

http://15.206.58.226/

Re-verified against the current deployed contract (see
`android/docs/API_CONTRACT.md`) before this build — no new endpoints were
invented; `POST /api/v1/tracking/telemetry/` does not exist on the backend,
this app correctly continues using the real, confirmed
`POST /api/v1/tracking/location/batch/`.

### Release

Version: 1.1.0
Version Code: 2

### Signing

Production-signed APK (v2/v3 signature schemes verified with `apksigner`).

### Known gaps / not verified in this release

- **No physical device or emulator was available in the build environment**
  — installation, real GPS, background/locked-screen tracking, offline queue
  draining against the live EC2 backend, and the web Live Map's marker
  movement were **not** end-to-end tested for this release. Treat this as the
  outstanding acceptance test before wider rollout — see BUILD_INFO.txt and
  the session's final report for exactly what was and wasn't verified.
- "Reached Site" has no backend confirmation — it will not appear on the web
  command dashboard until a corresponding backend endpoint is built.
