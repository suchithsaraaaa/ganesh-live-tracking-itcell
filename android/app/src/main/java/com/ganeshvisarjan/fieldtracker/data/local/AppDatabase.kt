package com.ganeshvisarjan.fieldtracker.data.local

import androidx.room.Database
import androidx.room.RoomDatabase
import com.ganeshvisarjan.fieldtracker.data.local.dao.ProcessionEventDao
import com.ganeshvisarjan.fieldtracker.data.local.dao.TelemetryDao
import com.ganeshvisarjan.fieldtracker.data.local.dao.TrackingSessionDao
import com.ganeshvisarjan.fieldtracker.data.local.entity.ProcessionEventEntity
import com.ganeshvisarjan.fieldtracker.data.local.entity.TelemetryPointEntity
import com.ganeshvisarjan.fieldtracker.data.local.entity.TrackingSessionEntity

@Database(
    entities = [
        TrackingSessionEntity::class,
        TelemetryPointEntity::class,
        ProcessionEventEntity::class,
    ],
    version = 1,
    exportSchema = true,
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun trackingSessionDao(): TrackingSessionDao
    abstract fun telemetryDao(): TelemetryDao
    abstract fun processionEventDao(): ProcessionEventDao

    companion object {
        const val DATABASE_NAME = "visarjan_tracking.db"
    }
}
