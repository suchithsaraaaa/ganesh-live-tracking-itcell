package com.ganeshvisarjan.fieldtracker.data.local.entity

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "telemetry_points",
    indices = [
        Index(value = ["syncStatus"]),
        Index(value = ["trackingSessionLocalId"]),
        Index(value = ["clientEventId"], unique = true),
    ],
)
data class TelemetryPointEntity(
    @PrimaryKey(autoGenerate = true) val localId: Long = 0,
    val clientEventId: String,
    val trackingSessionLocalId: String,
    val gpid: String,
    val latitude: Double,
    val longitude: Double,
    val accuracyMeters: Float?,
    val altitudeMeters: Double?,
    val speedMetersPerSecond: Float?,
    val bearingDegrees: Float?,
    val recordedAt: Long,
    val createdAt: Long,
    val syncStatus: String,
    val syncAttempts: Int,
    val lastSyncError: String?,
)
