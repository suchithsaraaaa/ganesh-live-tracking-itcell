package com.ganeshvisarjan.fieldtracker.data.repository

import com.ganeshvisarjan.fieldtracker.core.network.ApiResult
import com.ganeshvisarjan.fieldtracker.core.network.safeApiCall
import com.ganeshvisarjan.fieldtracker.data.local.dao.ProcessionEventDao
import com.ganeshvisarjan.fieldtracker.data.local.entity.ProcessionEventEntity
import com.ganeshvisarjan.fieldtracker.data.remote.api.ProcessionApi
import com.ganeshvisarjan.fieldtracker.data.remote.dto.ProcessionEventRequestDto
import com.ganeshvisarjan.fieldtracker.domain.model.GeoPoint
import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionEventRecord
import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionEventType
import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionState
import com.ganeshvisarjan.fieldtracker.domain.model.SyncStatus
import com.ganeshvisarjan.fieldtracker.domain.repository.ProcessionRepository
import com.ganeshvisarjan.fieldtracker.domain.usecase.ProcessionStateMachine
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import java.time.Instant
import java.util.UUID
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ProcessionRepositoryImpl @Inject constructor(
    private val processionApi: ProcessionApi,
    private val dao: ProcessionEventDao,
) : ProcessionRepository {

    override fun observeState(gpid: String): Flow<ProcessionState?> =
        dao.observeTimeline(gpid).map { entities -> deriveState(entities) }

    override fun observeTimeline(gpid: String): Flow<List<ProcessionEventRecord>> =
        dao.observeTimeline(gpid).map { entities -> entities.map { it.toDomain() } }

    override fun observePendingEventCount(): Flow<Int> = dao.observePendingCount()

    override suspend fun submitProcessionStart(
        gpid: String,
        assignmentId: String,
        location: GeoPoint,
        accuracyMeters: Float?,
    ): ApiResult<ProcessionState> {
        val occurredAt = System.currentTimeMillis()
        val result = safeApiCall {
            processionApi.startProcession(
                com.ganeshvisarjan.fieldtracker.data.remote.dto.ProcessionStartRequestDto(
                    assignmentId = assignmentId,
                    gpid = gpid,
                    latitude = location.latitude,
                    longitude = location.longitude,
                    accuracyMeters = accuracyMeters,
                    occurredAt = Instant.ofEpochMilli(occurredAt).toString(),
                ),
            )
        }
        return when (result) {
            is ApiResult.Error -> result
            is ApiResult.Success -> {
                dao.insert(
                    ProcessionEventEntity(
                        clientEventId = UUID.randomUUID().toString(),
                        gpid = gpid,
                        assignmentId = assignmentId,
                        trackingSessionLocalId = null,
                        eventType = ProcessionEventType.PROCESSION_STARTED.name,
                        occurredAt = occurredAt,
                        latitude = location.latitude,
                        longitude = location.longitude,
                        syncStatus = SyncStatus.SYNCED.name,
                        syncAttempts = 0,
                        lastSyncError = null,
                    ),
                )
                val state = ProcessionState.fromRaw(result.data.state) ?: ProcessionState.PROCESSION_STARTED
                ApiResult.Success(state)
            }
        }
    }

    override suspend fun recordLocalStart(
        gpid: String,
        assignmentId: String,
        trackingSessionLocalId: String?,
        location: GeoPoint,
    ) {
        dao.insert(
            ProcessionEventEntity(
                clientEventId = UUID.randomUUID().toString(),
                gpid = gpid,
                assignmentId = assignmentId,
                trackingSessionLocalId = trackingSessionLocalId,
                eventType = ProcessionEventType.PROCESSION_STARTED.name,
                occurredAt = System.currentTimeMillis(),
                latitude = location.latitude,
                longitude = location.longitude,
                // Already confirmed by the real backend call (tracking/start/)
                // that produced this session — nothing left to sync.
                syncStatus = SyncStatus.SYNCED.name,
                syncAttempts = 0,
                lastSyncError = null,
            ),
        )
    }

    override suspend fun submitEvent(
        gpid: String,
        assignmentId: String,
        trackingSessionLocalId: String?,
        eventType: ProcessionEventType,
        location: GeoPoint,
    ): ApiResult<ProcessionState> {
        val clientEventId = UUID.randomUUID().toString()
        val occurredAt = System.currentTimeMillis()

        dao.insert(
            ProcessionEventEntity(
                clientEventId = clientEventId,
                gpid = gpid,
                assignmentId = assignmentId,
                trackingSessionLocalId = trackingSessionLocalId,
                eventType = eventType.name,
                occurredAt = occurredAt,
                latitude = location.latitude,
                longitude = location.longitude,
                syncStatus = SyncStatus.PENDING.name,
                syncAttempts = 0,
                lastSyncError = null,
            ),
        )

        // Optimistic local resulting state — caller must treat this as provisional
        // until sync confirms it. Recomputed here rather than trusted from the caller.
        val optimisticState = deriveState(dao.getPendingChronological()) ?: ProcessionState.ASSIGNED

        // Try to sync immediately so the officer sees confirmation without waiting
        // for the next WorkManager pass; if it fails, the event just stays queued.
        syncPendingEvents()

        return ApiResult.Success(optimisticState)
    }

    override suspend fun syncPendingEvents(): ApiResult<Int> {
        val pending = dao.getPendingChronological()
        if (pending.isEmpty()) return ApiResult.Success(0)

        var uploaded = 0
        for (event in pending) {
            dao.markSyncing(listOf(event.localId))
            val result = safeApiCall {
                processionApi.submitEvent(
                    ProcessionEventRequestDto(
                        clientEventId = event.clientEventId,
                        assignmentId = event.assignmentId,
                        gpid = event.gpid,
                        eventType = event.eventType,
                        latitude = event.latitude,
                        longitude = event.longitude,
                        occurredAt = Instant.ofEpochMilli(event.occurredAt).toString(),
                    ),
                )
            }
            when (result) {
                is ApiResult.Success -> {
                    dao.markSynced(event.localId)
                    uploaded++
                }
                is ApiResult.Error -> {
                    dao.markFailed(event.localId, result.error.message)
                    // Preserve chronological order (spec section 24): stop at the first
                    // failure rather than uploading a later event out of sequence.
                    return if (uploaded > 0) ApiResult.Success(uploaded) else result
                }
            }
        }
        return ApiResult.Success(uploaded)
    }

    private fun deriveState(events: List<ProcessionEventEntity>): ProcessionState? {
        var state = ProcessionState.ASSIGNED
        var any = false
        events.sortedBy { it.occurredAt }.forEach { entity ->
            val type = ProcessionEventType.fromRaw(entity.eventType) ?: return@forEach
            val next = ProcessionStateMachine.resultingState(state, type)
            if (next != null) {
                state = next
                any = true
            }
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
    eventType = ProcessionEventType.fromRaw(eventType) ?: ProcessionEventType.MOVING,
    occurredAt = occurredAt,
    latitude = latitude,
    longitude = longitude,
    syncStatus = SyncStatus.valueOf(syncStatus),
    syncAttempts = syncAttempts,
    lastSyncError = lastSyncError,
)
