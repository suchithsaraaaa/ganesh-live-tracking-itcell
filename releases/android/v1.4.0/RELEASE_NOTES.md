# Hyderabad Police Ganesh Visarjan Live Tracking System
## Android Application Release Notes — v1.4.0 (versionCode: 4)

**Release Date**: 2026-09-24  
**Package**: `com.ganeshvisarjan.fieldtracker`  
**Artifact**: `releases/android/v1.4.0/TG-Police-Visarjan-Tracker-v1.4.0.apk`  
**Size**: 2,136,675 bytes (2.04 MB)  
**SHA-256**: `b2a3b5530f199f26399c3d878ccc0df683cf4e81220af697ec26310fae7f4651`  
**Signatures**: Verified APK Signature Scheme v2 & v3 (Release Key)  

---

### Executive Summary

Release **v1.4.0** addresses and resolves the root causes of field crashes occurring after tapping "START PROCESSION" and during active tracking recovery on Android 14+ devices. In addition, it elevates the Active Procession screen into a command interface featuring real-time telemetry diagnostics, full idol and jurisdiction metadata (GPID, height, police station, zone), and the complete operational lifecycle actions with confirmation safeguards.

---

### Critical Root Causes & Engineering Fixes

#### 1. FusedLocationProviderClient Looper Threading Crash (Fixed)
- **Root Cause**: `fusedClient.requestLocationUpdates(request, callback, null)` was invoked from a coroutine running on a worker thread (`Dispatchers.Default`), where `Looper.myLooper()` is null. Google Play Services threw an uncaught `IllegalStateException`/`IllegalArgumentException` ("Can't create handler inside thread that has not called Looper.prepare()"). The flow closed with an exception that terminated the process.
- **Fix**: Updated `LocationClient.kt` to explicitly supply `Looper.getMainLooper()` to `requestLocationUpdates()`, ensuring location callbacks are always delivered on the main looper. Defensively wrapped the flow in try-catch and `.catch { ... }` so GPS provider errors can never terminate the application.

#### 2. Android 14+ Foreground Service Contract Violation (Fixed)
- **Root Cause**: In `LocationTrackingService.kt`, an early return (`if (collectionJob?.isActive == true) return`) bypassed `startForeground()` when re-triggered by the OS or UI navigation. Android strictly enforces that any call to `startForegroundService()` must be followed by `Service.startForeground()` within 5–10 seconds, failing which the system terminates the process with `ForegroundServiceDidNotStartInTimeException`.
- **Fix**: Re-architected service startup to invoke `safeStartForeground(gpid)` unconditionally and synchronously on every start intent before checking job status. Service scope is backed by `SupervisorJob() + Dispatchers.Main.immediate + CoroutineExceptionHandler`.

#### 3. Active Session Recovery & Crash Safety (Fixed)
- **Root Cause**: Opening "OPEN ACTIVE TRACKING" crashed if active assignment details or network state had not loaded yet, or if navigation re-entered the back-stack.
- **Fix**: `TrackingViewModel` and `TrackingScreen` now resiliently bind to both local Room data and backend state. If active assignment is not immediately cached, the screen defaults cleanly to the session GPID and automatically fetches assignment details in the background without blocking the UI. `NavGraph` uses `launchSingleTop = true` to prevent duplicate screen instances.

---

### New Features & Lifecycle Enhancements

1. **Complete Procession Lifecycle Engine**:
   - Implements full state machine:
     $$\text{ASSIGNED} \to \text{REACHED SITE} \to \text{PROCESSION STARTED} \to \text{REACHED VISARJAN SITE} \to (\text{VISARJAN DONE} \mid \text{VISARJAN NOT DONE}) \to \text{SENT TO HOLDING} \to \text{RETURNED TO ORIGIN}$$
   - **Operational Action Triggers**:
     - At `PROCESSION STARTED`: `[ REACHED VISARJAN SITE ]`
     - At `REACHED VISARJAN SITE`: `[ VISARJAN DONE ]` (primary green) and `[ VISARJAN NOT DONE ]` (amber)
     - At `VISARJAN_NOT_DONE`: `[ SEND TO HOLDING ]`
     - At `SENT_TO_HOLDING`: `[ RETURN TO ORIGIN ]`
     - At `VISARJAN_DONE` / `RETURNED_TO_ORIGIN`: Displays "Procession Concluded" banner.
   - **Confirmation Safeguards**: Interactive `AlertDialog` verification before committing irreversible actions (`VISARJAN DONE`, `VISARJAN NOT DONE`, and `STOP TRACKING`).

2. **Idol & Jurisdiction Operational Identity**:
   - Prominent GPID header in bold monospace font.
   - Idol name / Pandal association name.
   - Idol height in feet with color-coded classification badge (Red: >26ft, Yellow: 21-26ft, Green: 15-21ft).
   - Police Station and Zone indicators (e.g. "Chatrinaka PS • South Zone").

3. **Field GPS Telemetry & Sync Diagnostics**:
   - Real-time coordinates displayed to 6 decimal places.
   - GPS horizontal accuracy readout with color indicators (Green: $\le 30$m, Yellow: $>30$m).
   - Timestamp of latest satellite fix.
   - Network connectivity indicator (Connected to Command Center vs Offline Local Mode).
   - Offline telemetry queue status (Synced vs X points queued in Room database).

---

### Backend API Alignment (EC2 Deployed)

- **New Endpoint**: `POST /api/v1/tracking/events/`
- **Model**: `IdolEvent` updated with `REACHED_SITE`, `VISARJAN_NOT_DONE`, `SENT_TO_HOLDING`, and `RETURNED_TO_ORIGIN`.
- **Idempotency**: Deduplication via `client_event_id` in metadata.
- **Migration**: `0006_alter_idolevent_event_type.py` applied on EC2 (`15.206.58.226`).
- **Tests**: All 29 Django backend tracking tests passing (`python manage.py test apps.tracking`).

---

### Quality Assurance & Verification Summary

| Test Suite / Tool | Command / Action | Result |
| :--- | :--- | :--- |
| **Android Unit Tests** | `gradlew.bat :app:testMockDebugUnitTest` | **PASSED** (12 tasks executed, 36 total) |
| **Android Test Compilation** | `gradlew.bat :app:compileProdDebugAndroidTestKotlin` | **PASSED** (14 tasks executed, 32 total) |
| **Release Build** | `gradlew.bat :app:assembleProdRelease` | **PASSED** (BUILD SUCCESSFUL in 4m 10s) |
| **Signature Verification** | `apksigner.bat verify --verbose` | **VERIFIED** (v2: true, v3: true, 1 signer) |
| **Manifest & Badging** | `aapt2.exe dump badging` | `versionCode='4'`, `versionName='1.4.0'` |
| **Permission Audit** | `aapt2.exe dump badging` | No `ACCESS_BACKGROUND_LOCATION` |
| **Backend Integration Tests** | `python manage.py test apps.tracking` | **29/29 PASSED** |
| **EC2 Container Health** | `docker compose ps` | `backend-1`, `db-1`, `nginx-1` **ALL HEALTHY** |

---

### Installation on Constable Devices

Transfer and install the APK via ADB or local download:
```bash
adb install -r releases/android/v1.4.0/TG-Police-Visarjan-Tracker-v1.4.0.apk
```
Or download directly from the distribution directory.
