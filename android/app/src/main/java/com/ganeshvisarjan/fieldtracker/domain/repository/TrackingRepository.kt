package com.ganeshvisarjan.fieldtracker.domain.repository

import com.ganeshvisarjan.fieldtracker.core.network.ApiResult
import com.ganeshvisarjan.fieldtracker.domain.model.GeoPoint
import com.ganeshvisarjan.fieldtracker.domain.model.TrackingSession
import kotlinx.coroutines.flow.Flow

/**
 * Owns the tracking-session lifecycle and the durable local telemetry queue
 * (spec sections 13-26). GPS points are NEVER sent straight to the network —
 * every accepted fix goes: validate → Room insert → (later) sync attempt.
 * Losing a point because a POST failed is explicitly unacceptable.
 */
interface TrackingRepository {

    /**
     * Starts a session via the confirmed `POST /tracking/start/`
     * (`StartTrackingView`) — the real, authoritative start action; there is
     * no separate procession-start endpoint (see docs/API_CONTRACT.md).
     * [officerLocation] must be a fresh fix, always sent regardless of where
     * it is: as of the 2026-09-23 product decision, this app does not compute
     * or care about any distance from the idol's registered origin — that is
     * purely reference data now (see [com.ganeshvisarjan.fieldtracker.domain.model.Idol.originLocation]).
     * Whatever the backend itself currently validates the request against is
     * entirely its own concern; this call submits and reacts to the response,
     * nothing more. Persists the resulting session (including the actual
     * start [officerLocation], not just the server id) locally.
     */
    suspend fun startSession(
        assignmentId: String,
        gpid: String,
        officerLocation: GeoPoint,
        officerAccuracyMeters: Float?,
        deviceInfo: String,
    ): ApiResult<TrackingSession>

    /** Marks the session STOP_REQUESTED locally (works offline) and lets the sync worker finalize it. */
    suspend fun requestStopSession(localSessionId: String)

    fun observeActiveSession(): Flow<TrackingSession?>

    /** Validates and durably persists one GPS fix. Returns false if the fix failed quality checks. */
    suspend fun recordTelemetryPoint(
        sessionLocalId: String,
        gpid: String,
        location: GeoPoint,
        accuracyMeters: Float?,
        altitudeMeters: Double?,
        speedMetersPerSecond: Float?,
        bearingDegrees: Float?,
        recordedAt: Long,
    ): Boolean

    fun observePendingTelemetryCount(): Flow<Int>
    fun observeLastSyncError(): Flow<String?>

    /** Invoked by [com.ganeshvisarjan.fieldtracker.worker.TelemetrySyncWorker]; batches + uploads pending points. */
    suspend fun syncPendingTelemetry(): ApiResult<Int>

    /**
     * If a session is STOP_REQUESTED and all its telemetry has synced, calls the
     * backend stop endpoint and marks it STOPPED. Safe to call repeatedly — a
     * no-op when nothing is ready to finalize (spec section 24: don't lose the
     * stop request if the network is down when the officer taps Stop).
     */
    suspend fun finalizeStopIfReady(): ApiResult<Unit>?
}
