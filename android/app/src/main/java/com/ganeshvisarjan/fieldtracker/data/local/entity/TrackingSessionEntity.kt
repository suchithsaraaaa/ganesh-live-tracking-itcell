package com.ganeshvisarjan.fieldtracker.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "tracking_sessions")
data class TrackingSessionEntity(
    @PrimaryKey val localSessionId: String,
    val serverSessionId: String?,
    val gpid: String,
    val assignmentId: String,
    val startedAt: Long,
    val stoppedAt: Long?,
    val status: String,
    /**
     * The officer's actual fresh GPS fix at the moment Start Procession was
     * pressed and sent to the backend (`POST /tracking/start/`) — persisted
     * locally rather than only sent over the wire and discarded, per the
     * 2026-09-23 product decision's requirement that the real start position
     * be recorded, distinct from [com.ganeshvisarjan.fieldtracker.domain.model.Idol.originLocation]
     * (reference data) and from subsequent telemetry (current location).
     */
    val startLatitude: Double?,
    val startLongitude: Double?,
)
