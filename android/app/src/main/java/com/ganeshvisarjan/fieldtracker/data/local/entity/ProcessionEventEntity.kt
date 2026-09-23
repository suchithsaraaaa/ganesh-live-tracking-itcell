package com.ganeshvisarjan.fieldtracker.data.local.entity

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "procession_events",
    indices = [
        Index(value = ["syncStatus"]),
        Index(value = ["gpid"]),
        Index(value = ["clientEventId"], unique = true),
    ],
)
data class ProcessionEventEntity(
    @PrimaryKey(autoGenerate = true) val localId: Long = 0,
    val clientEventId: String,
    val gpid: String,
    val assignmentId: String,
    val trackingSessionLocalId: String?,
    val eventType: String,
    val occurredAt: Long,
    val latitude: Double,
    val longitude: Double,
    val syncStatus: String,
    val syncAttempts: Int,
    val lastSyncError: String?,
)
