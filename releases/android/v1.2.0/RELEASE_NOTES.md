# TG Police Visarjan Tracker — Release Notes

## Version 1.2.0 (Build 3) — Production Release

### Key Fixes & Improvements
- **Removed Background Location Requirement**: Completely removed `ACCESS_BACKGROUND_LOCATION` from `AndroidManifest.xml` and application code. Setup card no longer blocks or requests "Allow all the time", displaying **`LOCATION READY`** immediately once precise GPS, location services, and notifications are granted.
- **Continuous Screen-Lock Tracking via Foreground Service**: Continuous background and locked-screen tracking is fully supported using Android's standard `FOREGROUND_SERVICE_LOCATION` architecture with persistent service notification and a leak-proof partial `WakeLock`.
- **Fixed Start Procession (Start-Gate Removed)**: Removed all legacy 50-meter pandal proximity restrictions, geocoding confidence requirements, and unresolved idol origin blocks from `POST /api/v1/tracking/start/`. Procession start is now governed purely by authenticated officer identity, active assignment, and valid live GPS fix.
- **Fixed Reached Site Crash**: Eliminated the `SecurityException` crash when tapping "I'VE REACHED THE SITE". `LocationClient` verifies runtime location permissions before querying Google Play Services, returning safely without process termination.
- **Fixed Permission Request Flow**: Implemented Compose Activity Result contracts (`RequestMultiplePermissions`, `RequestPermission`), allowing direct permission requests from the UI with automatic resume refresh via `LifecycleEventObserver`.
- **State-Aware Setup UI**: Cleaned up the `LOCATION SETUP REQUIRED` / `LOCATION READY` card to present only actual prerequisites (Precise GPS, Location Services, Persistent Notification).
- **Hardened Foreground GPS Tracking**: Upgraded `LocationTrackingService` with `ServiceCompat.startForeground` specifying `FOREGROUND_SERVICE_TYPE_LOCATION` (Android 14+ / Q+ compliance) and clear identity headers (`TG Police Visarjan Tracker`, `Procession tracking active`, `GPID: <gpid>`).
- **Preserved Offline Telemetry Queue**: Maintained durable Room-backed telemetry persistence and background WorkManager batch synchronization (`POST /api/v1/tracking/location/batch/`).
- **Production Build & Signing**: Built with R8 optimization, minification, and resource shrinking; signed with production key `visarjan_release` using APK Signature Schemes v2 and v3.
