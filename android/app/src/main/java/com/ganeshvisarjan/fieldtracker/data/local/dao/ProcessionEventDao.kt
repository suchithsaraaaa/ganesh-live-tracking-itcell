package com.ganeshvisarjan.fieldtracker.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.ganeshvisarjan.fieldtracker.data.local.entity.ProcessionEventEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface ProcessionEventDao {

    @Insert(onConflict = OnConflictStrategy.IGNORE)
    suspend fun insert(event: ProcessionEventEntity): Long

    @Query("SELECT * FROM procession_events WHERE syncStatus IN ('PENDING', 'FAILED') ORDER BY occurredAt ASC")
    suspend fun getPendingChronological(): List<ProcessionEventEntity>

    @Query("UPDATE procession_events SET syncStatus = 'SYNCING' WHERE localId IN (:ids)")
    suspend fun markSyncing(ids: List<Long>)

    @Query("UPDATE procession_events SET syncStatus = 'SYNCED' WHERE localId = :id")
    suspend fun markSynced(id: Long)

    @Query(
        "UPDATE procession_events SET syncStatus = 'FAILED', syncAttempts = syncAttempts + 1, lastSyncError = :error " +
            "WHERE localId = :id",
    )
    suspend fun markFailed(id: Long, error: String)

    @Query("SELECT COUNT(*) FROM procession_events WHERE syncStatus IN ('PENDING', 'FAILED', 'SYNCING')")
    fun observePendingCount(): Flow<Int>

    @Query("SELECT * FROM procession_events WHERE gpid = :gpid ORDER BY occurredAt ASC")
    fun observeTimeline(gpid: String): Flow<List<ProcessionEventEntity>>

    @Query("SELECT * FROM procession_events WHERE gpid = :gpid AND syncStatus = 'SYNCED' ORDER BY occurredAt DESC LIMIT 1")
    fun observeLastSyncedEvent(gpid: String): Flow<ProcessionEventEntity?>
}
