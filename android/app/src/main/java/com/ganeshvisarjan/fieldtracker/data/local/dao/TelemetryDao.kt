package com.ganeshvisarjan.fieldtracker.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.ganeshvisarjan.fieldtracker.data.local.entity.TelemetryPointEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface TelemetryDao {

    @Insert(onConflict = OnConflictStrategy.IGNORE)
    suspend fun insert(point: TelemetryPointEntity): Long

    @Query("SELECT * FROM telemetry_points WHERE syncStatus IN ('PENDING', 'FAILED') ORDER BY recordedAt ASC LIMIT :limit")
    suspend fun getPending(limit: Int): List<TelemetryPointEntity>

    @Query("UPDATE telemetry_points SET syncStatus = 'SYNCING' WHERE localId IN (:ids)")
    suspend fun markSyncing(ids: List<Long>)

    @Query("UPDATE telemetry_points SET syncStatus = 'SYNCED' WHERE localId IN (:ids)")
    suspend fun markSynced(ids: List<Long>)

    @Query(
        "UPDATE telemetry_points SET syncStatus = 'FAILED', syncAttempts = syncAttempts + 1, lastSyncError = :error " +
            "WHERE localId IN (:ids)",
    )
    suspend fun markFailed(ids: List<Long>, error: String)

    @Query("DELETE FROM telemetry_points WHERE syncStatus = 'SYNCED'")
    suspend fun deleteSynced(): Int

    @Query("SELECT COUNT(*) FROM telemetry_points WHERE syncStatus IN ('PENDING', 'FAILED', 'SYNCING')")
    fun observePendingCount(): Flow<Int>

    @Query("SELECT * FROM telemetry_points WHERE trackingSessionLocalId = :sessionLocalId ORDER BY recordedAt ASC")
    fun observeSessionPoints(sessionLocalId: String): Flow<List<TelemetryPointEntity>>

    @Query("SELECT lastSyncError FROM telemetry_points WHERE lastSyncError IS NOT NULL ORDER BY localId DESC LIMIT 1")
    fun observeLastError(): Flow<String?>
}
