package com.ganeshvisarjan.fieldtracker.domain.model

/**
 * An operational lifecycle event (PROCESSION_STARTED, MOVING, ...) — DIFFERENT
 * from [TelemetryPoint] (spec section 21/37). Not every GPS point is an event,
 * and events are never fabricated from GPS proximity alone.
 *
 * [clientEventId] follows the same idempotency contract as [TelemetryPoint] —
 * generated once, reused on every retry of the same local event.
 */
data class ProcessionEventRecord(
    val localId: Long,
    val clientEventId: String,
    val gpid: String,
    val assignmentId: String,
    val trackingSessionLocalId: String?,
    val eventType: ProcessionEventType,
    val occurredAt: Long, // device timestamp — when the officer actually acted
    val latitude: Double,
    val longitude: Double,
    val syncStatus: SyncStatus,
    val syncAttempts: Int,
    val lastSyncError: String?,
)
