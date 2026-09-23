package com.ganeshvisarjan.fieldtracker.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.ganeshvisarjan.fieldtracker.data.local.entity.TrackingSessionEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface TrackingSessionDao {

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(session: TrackingSessionEntity)

    @Query("SELECT * FROM tracking_sessions WHERE status NOT IN ('STOPPED', 'SYNCED', 'FAILED') ORDER BY startedAt DESC LIMIT 1")
    fun observeActiveSession(): Flow<TrackingSessionEntity?>

    @Query("SELECT * FROM tracking_sessions WHERE status NOT IN ('STOPPED', 'SYNCED', 'FAILED') ORDER BY startedAt DESC LIMIT 1")
    suspend fun getActiveSessionOnce(): TrackingSessionEntity?

    @Query("SELECT * FROM tracking_sessions WHERE localSessionId = :localId")
    suspend fun getById(localId: String): TrackingSessionEntity?

    @Query("UPDATE tracking_sessions SET status = :status WHERE localSessionId = :localId")
    suspend fun updateStatus(localId: String, status: String)

    @Query("UPDATE tracking_sessions SET status = :status, stoppedAt = :stoppedAt WHERE localSessionId = :localId")
    suspend fun markStopped(localId: String, status: String, stoppedAt: Long)

    @Query("UPDATE tracking_sessions SET serverSessionId = :serverSessionId WHERE localSessionId = :localId")
    suspend fun setServerSessionId(localId: String, serverSessionId: String)
}
