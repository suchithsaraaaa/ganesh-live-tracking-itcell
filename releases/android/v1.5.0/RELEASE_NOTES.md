# Hyderabad Police Ganesh Visarjan Live Tracking System
## Android Application Release Notes — v1.5.0 (versionCode: 5)

**Release Date**: 2026-09-24  
**Package**: `com.ganeshvisarjan.fieldtracker`  
**Artifact**: `releases/android/v1.5.0/TG-Police-Visarjan-Tracker-v1.5.0.apk`  
**Size**: 2,136,672 bytes (2.04 MB)  
**SHA-256**: `a3c49fa63701cc240478985f4aca0fd360b6de5119ff7e0702ed04d96e5fe785`  
**Signatures**: Verified APK Signature Scheme v2 & v3 (Release Key)  

---

### Executive Summary

Release **v1.5.0** is the companion release to the Web Application's **Admin Force-End Assignment + Immediate Officer Release** engine. It equips field devices with authoritative remote termination detection, background service shutdown safety, idempotent telemetry draining, and clean state recovery when an administrator terminates an active procession assignment from the command center.

---

### Key Capabilities & Engineering Hardening

#### 1. Authoritative Remote Admin Termination Handling
- **Explicit Terminal State**: Added `REMOTELY_TERMINATED` to `TrackingSessionStatus`.
- **Zero False-Positive Termination**: Network dropouts, 500s, timeouts, socket disconnects, or authentication refresh retries are strictly handled by the offline retry queue and **NEVER** misclassified as an assignment termination. Only an authoritative server response (`active_assignment == null` or assignment ID mismatch) triggers remote termination reconciliation.
- **Immediate State Transition**: When administrative termination is confirmed by the backend, `TrackingViewModel` and `HomeViewModel`:
  1. Immediately mark the local Room tracking session as `REMOTELY_TERMINATED`.
  2. Send `ACTION_STOP` to `LocationTrackingService` to safely stop foreground GPS tracking.
  3. Flush eligible cached telemetry without fabricating timestamps or coordinates.
  4. Display the authoritative notification: *"Tracking was ended by an administrator."*
  5. Clear active-session UI state, permanently removing *"OPEN ACTIVE TRACKING"* for the terminated duty.

#### 2. GPS Callback & Foreground Service Safety
- **Race Condition Immunity**: In `LocationTrackingService`, the location updates collector verifies that the session is still active and valid before recording fixes. If the session has become terminal (`REMOTELY_TERMINATED`, `STOPPED`, `FAILED`, `SYNCED`), incoming GPS callbacks are discarded safely and `stopTracking()` shuts down the foreground service without crashing.
- **Idempotent Service Lifecycle**: Multiple consecutive `ACTION_START` or `ACTION_STOP` intents execute cleanly without leaking wake locks, duplicate notification channels, or crashing coroutine scopes.

#### 3. Clean Reassignment & Identity Isolation
- **Room Exclusion Guarantees**: Updated `TrackingSessionDao` to exclude `REMOTELY_TERMINATED` from `observeActiveSession()` and `getActiveSessionOnce()`.
- **Zero Cross-Assignment Leakage**: When the command center assigns the released officer to a new GPID, Android loads the new assignment with a completely clean state. Old GPIDs, session IDs, and lifecycle states never leak into the subsequent procession.

---

### Verification Summary

1. **Gradle Compilation & Lint Checks**:
   - `assembleProdRelease`: **BUILD SUCCESSFUL**
   - R8 Minification, Resource Shrinking & APK Alignment verified.
   - APK Signature Scheme v2 & v3 verified.

2. **Automated Unit Test Suite**:
   - `:app:testMockDebugUnitTest`: **BUILD SUCCESSFUL** (All unit tests passed).
   - Tested:
     - `getActiveSessionOnce` active domain mapping and exclusion of terminal sessions.
     - `terminateSessionRemotely` timestamping and `REMOTELY_TERMINATED` Room state.
     - `recordTelemetryPoint` rejection and telemetry protection after administrative termination.
     - `ServiceRestartDecision` returning `DoNothing` for terminated sessions.
     - Repeated remote termination safety and idempotency.

---

### Production Deployment Details

- **Application ID**: `com.ganeshvisarjan.fieldtracker`
- **Version Name**: `1.5.0`
- **Version Code**: `5`
- **Minimum SDK**: `26` (Android 8.0)
- **Target SDK**: `34` (Android 14)
- **Signing Scheme**: v2 & v3 enabled
