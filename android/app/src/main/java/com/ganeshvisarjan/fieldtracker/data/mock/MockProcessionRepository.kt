package com.ganeshvisarjan.fieldtracker.data.mock

import com.ganeshvisarjan.fieldtracker.core.network.ApiResult
import com.ganeshvisarjan.fieldtracker.data.local.dao.ProcessionEventDao
import com.ganeshvisarjan.fieldtracker.data.local.entity.ProcessionEventEntity
import com.ganeshvisarjan.fieldtracker.domain.model.GeoPoint
import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionEventRecord
import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionEventType
import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionState
import com.ganeshvisarjan.fieldtracker.domain.model.SyncStatus
import com.ganeshvisarjan.fieldtracker.domain.repository.ProcessionRepository
import com.ganeshvisarjan.fieldtracker.domain.usecase.ProcessionStateMachine
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import java.util.UUID
import javax.inject.Inject
import javax.inject.Singleton

/** Same Room-backed timeline as production; every network call is simulated with a short delay. */
@Singleton
class MockProcessionRepository @Inject constructor(
    private val dao: ProcessionEventDao,
) : ProcessionRepository {

    override fun observeState(gpid: String): Flow<ProcessionState?> =
        dao.observeTimeline(gpid).map { deriveState(it) }

    override fun observeTimeline(gpid: String): Flow<List<ProcessionEventRecord>> =
        dao.observeTimeline(gpid).map { list -> list.map { it.toDomain() } }

    override fun observePendingEventCount(): Flow<Int> = dao.observePendingCount()

    override suspend fun submitProcessionStart(
        gpid: String,
        assignmentId: String,
        location: GeoPoint,
        accuracyMeters: Float?,
    ): ApiResult<ProcessionState> {
        delay(300)
        insertSynced(gpid, assignmentId, ProcessionEventType.PROCESSION_STARTED, location)
        return ApiResult.Success(ProcessionState.PROCESSION_STARTED)
    }

    override suspend fun recordLocalStart(
        gpid: String,
        assignmentId: String,
        trackingSessionLocalId: String?,
        location: GeoPoint,
    ) {
        insertSynced(gpid, assignmentId, ProcessionEventType.PROCESSION_STARTED, location)
    }

    override suspend fun submitEvent(
        gpid: String,
        assignmentId: String,
        trackingSessionLocalId: String?,
        eventType: ProcessionEventType,
        location: GeoPoint,
    ): ApiResult<ProcessionState> {
        val clientEventId = UUID.randomUUID().toString()
        dao.insert(
            ProcessionEventEntity(
                clientEventId = clientEventId,
                gpid = gpid,
                assignmentId = assignmentId,
                trackingSessionLocalId = trackingSessionLocalId,
                eventType = eventType.name,
                occurredAt = System.currentTimeMillis(),
                latitude = location.latitude,
                longitude = location.longitude,
                syncStatus = SyncStatus.PENDING.name,
                syncAttempts = 0,
                lastSyncError = null,
            ),
        )
        syncPendingEvents()
        val state = deriveState(dao.getPendingChronological()) ?: ProcessionState.ASSIGNED
        return ApiResult.Success(state)
    }

    override suspend fun syncPendingEvents(): ApiResult<Int> {
        val pending = dao.getPendingChronological()
        if (pending.isEmpty()) return ApiResult.Success(0)
        delay(300)
        pending.forEach { dao.markSynced(it.localId) }
        return ApiResult.Success(pending.size)
    }

    private suspend fun insertSynced(gpid: String, assignmentId: String, type: ProcessionEventType, location: GeoPoint) {
        dao.insert(
            ProcessionEventEntity(
                clientEventId = UUID.randomUUID().toString(),
                gpid = gpid,
                assignmentId = assignmentId,
                trackingSessionLocalId = null,
                eventType = type.name,
                occurredAt = System.currentTimeMillis(),
                latitude = location.latitude,
                longitude = location.longitude,
                syncStatus = SyncStatus.SYNCED.name,
                syncAttempts = 0,
                lastSyncError = null,
            ),
        )
    }

    private fun deriveState(events: List<ProcessionEventEntity>): ProcessionState? {
        var state = ProcessionState.ASSIGNED
        var any = false
        events.sortedBy { it.occurredAt }.forEach { entity ->
            val type = ProcessionEventType.fromRaw(entity.eventType) ?: return@forEach
            ProcessionStateMachine.resultingState(state, type)?.let { state = it; any = true }
        }
        return if (any) state else null
    }
}

private fun ProcessionEventEntity.toDomain() = ProcessionEventRecord(
    localId = localId,
    clientEventId = clientEventId,
    gpid = gpid,
    assignmentId = assignmentId,
    trackingSessionLocalId = trackingSessionLocalId,
    eventType = ProcessionEventType.fromRaw(eventType) ?: ProcessionEventType.PROCESSION_STARTED,
    occurredAt = occurredAt,
    latitude = latitude,
    longitude = longitude,
    syncStatus = SyncStatus.valueOf(syncStatus),
    syncAttempts = syncAttempts,
    lastSyncError = lastSyncError,
)
