package com.ganeshvisarjan.fieldtracker.domain.model

enum class SyncStatus { PENDING, SYNCING, SYNCED, FAILED }

/**
 * One raw GPS fix. Latitude/longitude are always separate Doubles — never a
 * combined "lat,lon" string (spec section 14). [recordedAt] is the
 * device-reported fix time; [receivedAt] (set by the backend on ingest) is a
 * different concept and is never substituted for it (spec section 53).
 *
 * [clientEventId] is a stable UUID generated once per point and reused on every
 * retry, so the backend can deduplicate if its API supports idempotency
 * (spec section 20) — the app must never mint a new id for the same local point.
 */
data class TelemetryPoint(
    val localId: Long,
    val clientEventId: String,
    val trackingSessionLocalId: String,
    val gpid: String,
    val latitude: Double,
    val longitude: Double,
    val accuracyMeters: Float?,
    val altitudeMeters: Double?,
    val speedMetersPerSecond: Float?,
    val bearingDegrees: Float?,
    val recordedAt: Long, // epoch millis UTC, device clock
    val createdAt: Long,  // epoch millis UTC, when Room persisted it
    val syncStatus: SyncStatus,
    val syncAttempts: Int,
    val lastSyncError: String?,
)
