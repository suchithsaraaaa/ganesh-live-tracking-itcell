# TG Police Visarjan Tracker — Release Notes

## Version 1.3.0 (Build 4) — Production Release

### Summary
Release v1.3.0 packages the complete production resolution for field operation on Android devices. It completely eliminates the background location permission requirement from both the application manifest and UI, fixes the permission and site-reach flows, and aligns the backend start-gate so officers can reliably initiate procession tracking from their live GPS position.

### Key Changes & Fixes
- **Version Bump**: Bumped to `versionName = "1.3.0"`, `versionCode = 4`.
- **Background Location Completely Removed**: Removed `ACCESS_BACKGROUND_LOCATION` from `AndroidManifest.xml`, permission utilities, and Compose UI screens. The application no longer requests "Allow all the time" or shows background location as a required setup item.
- **Immediate Setup Readiness**: The `LOCATION SETUP REQUIRED` card transitions to **`LOCATION READY`** as soon as precise GPS, location services, and notifications are granted.
- **Continuous Screen-Lock Tracking**: Procession tracking with screen locked and app backgrounded is fully sustained through Android's standard `FOREGROUND_SERVICE_LOCATION` architecture with persistent notification and battery-conscious partial `WakeLock`.
- **Eliminated Start-Gate Pandal Restrictions**: Backend `POST /api/v1/tracking/start/` no longer enforces 50m origin proximity or geocoding confidence checks. Authorized officers can start tracking directly with their active assignment and valid GPS fix.
- **Robust Site Confirmation**: Resolved previous `SecurityException` crash when tapping "I'VE REACHED THE SITE" with safe permission checks and persisted local setup state.
- **Full Offline Resilience**: Offline telemetry is queued in Room database and automatically synchronized in batches via WorkManager once connectivity resumes.
- **Production Signing**: Signed with production release keystore (`visarjan_release`) using APK Signature Scheme v2 and v3.
