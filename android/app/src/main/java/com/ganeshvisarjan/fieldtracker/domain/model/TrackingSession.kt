package com.ganeshvisarjan.fieldtracker.domain.model

/**
 * Avoid contradictory states (spec section 25): this is the ONE status field for
 * a tracking session, not a set of independent booleans.
 */
enum class TrackingSessionStatus {
    NOT_STARTED,
    STARTING,
    ACTIVE,
    STOP_REQUESTED,
    STOPPED,
    REMOTELY_TERMINATED,
    SYNC_PENDING,
    SYNCED,
    FAILED,
}

/**
 * Local tracking-session record. [sessionId] is null until the backend has
 * acknowledged session start and issued its own id (spec section 51) — the app
 * must never treat a locally generated id as authoritative once the real one exists.
 * [localSessionId] is the Room primary key and is always present, so the app can
 * track a session that started while offline before the server id exists.
 */
data class TrackingSession(
    val localSessionId: String,
    val serverSessionId: String?,
    val gpid: String,
    val assignmentId: String,
    val startedAt: Long, // epoch millis, UTC
    val stoppedAt: Long?,
    val status: TrackingSessionStatus,
    /** The officer's actual GPS fix when Start Procession was pressed — see [com.ganeshvisarjan.fieldtracker.data.local.entity.TrackingSessionEntity]. */
    val startLocation: GeoPoint? = null,
)
