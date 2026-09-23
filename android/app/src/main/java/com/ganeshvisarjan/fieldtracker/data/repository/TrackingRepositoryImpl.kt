package com.ganeshvisarjan.fieldtracker.data.repository

import com.ganeshvisarjan.fieldtracker.core.config.AppConfig
import com.ganeshvisarjan.fieldtracker.core.logging.TrackingLog
import com.ganeshvisarjan.fieldtracker.core.network.ApiError
import com.ganeshvisarjan.fieldtracker.core.network.ApiResult
import com.ganeshvisarjan.fieldtracker.core.network.safeApiCall
import com.ganeshvisarjan.fieldtracker.data.local.dao.TelemetryDao
import com.ganeshvisarjan.fieldtracker.data.local.dao.TrackingSessionDao
import com.ganeshvisarjan.fieldtracker.data.local.entity.TelemetryPointEntity
import com.ganeshvisarjan.fieldtracker.data.local.entity.TrackingSessionEntity
import com.ganeshvisarjan.fieldtracker.data.remote.api.TrackingApi
import com.ganeshvisarjan.fieldtracker.data.remote.dto.StartTrackingRequestDto
import com.ganeshvisarjan.fieldtracker.data.remote.dto.StopTrackingRequestDto
import com.ganeshvisarjan.fieldtracker.data.remote.dto.TelemetryBatchRequestDto
import com.ganeshvisarjan.fieldtracker.data.remote.dto.TelemetryPointDto
import com.ganeshvisarjan.fieldtracker.domain.model.GeoPoint
import com.ganeshvisarjan.fieldtracker.domain.model.TrackingSession
import com.ganeshvisarjan.fieldtracker.domain.model.TrackingSessionStatus
import com.ganeshvisarjan.fieldtracker.domain.repository.TrackingRepository
import com.ganeshvisarjan.fieldtracker.domain.usecase.GpsQualityValidator
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import java.time.Instant
import java.util.UUID
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class TrackingRepositoryImpl @Inject constructor(
    private val trackingApi: TrackingApi,
    private val sessionDao: TrackingSessionDao,
    private val telemetryDao: TelemetryDao,
    private val gpsQualityValidator: GpsQualityValidator,
) : TrackingRepository {

    override suspend fun startSession(
        assignmentId: String,
        gpid: String,
        officerLocation: GeoPoint,
        officerAccuracyMeters: Float?,
        deviceInfo: String,
    ): ApiResult<TrackingSession> {
        val localId = UUID.randomUUID().toString()
        val startedAt = System.currentTimeMillis()

        val result = safeApiCall {
            trackingApi.startTracking(
                StartTrackingRequestDto(
                    assignmentId = assignmentId,
                    gpid = gpid,
                    latitude = officerLocation.latitude,
                    longitude = officerLocation.longitude,
                    deviceInfo = deviceInfo,
                ),
            )
        }

        return when (result) {
            is ApiResult.Success -> {
                val dto = result.data
                sessionDao.upsert(
                    TrackingSessionEntity(
                        localSessionId = localId,
                        serverSessionId = dto.id,
                        gpid = gpid,
                        assignmentId = assignmentId,
                        startedAt = startedAt,
                        stoppedAt = null,
                        status = TrackingSessionStatus.ACTIVE.name,
                        startLatitude = officerLocation.latitude,
                        startLongitude = officerLocation.longitude,
                    ),
                )
                TrackingLog.sessionStarted(dto.id)
                ApiResult.Success(
                    TrackingSession(
                        localId, dto.id, gpid, assignmentId, startedAt, null,
                        TrackingSessionStatus.ACTIVE, officerLocation,
                    ),
                )
            }
            is ApiResult.Error -> result
        }
    }

    override suspend fun requestStopSession(localSessionId: String) {
        sessionDao.updateStatus(localSessionId, TrackingSessionStatus.STOP_REQUESTED.name)
    }

    override fun observeActiveSession(): Flow<TrackingSession?> =
        sessionDao.observeActiveSession().map { it?.toDomain() }

    override suspend fun recordTelemetryPoint(
        sessionLocalId: String,
        gpid: String,
        location: GeoPoint,
        accuracyMeters: Float?,
        altitudeMeters: Double?,
        speedMetersPerSecond: Float?,
        bearingDegrees: Float?,
        recordedAt: Long,
    ): Boolean {
        if (!gpsQualityValidator.isAcceptable(location, accuracyMeters)) return false

        TrackingLog.gpsFix(accuracyMeters)
        val id = telemetryDao.insert(
            TelemetryPointEntity(
                clientEventId = UUID.randomUUID().toString(),
                trackingSessionLocalId = sessionLocalId,
                gpid = gpid,
                latitude = location.latitude,
                longitude = location.longitude,
                accuracyMeters = accuracyMeters,
                altitudeMeters = altitudeMeters,
                speedMetersPerSecond = speedMetersPerSecond,
                bearingDegrees = bearingDegrees,
                recordedAt = recordedAt,
                createdAt = System.currentTimeMillis(),
                syncStatus = "PENDING",
                syncAttempts = 0,
                lastSyncError = null,
            ),
        )
        TrackingLog.pointStored(id)
        return true
    }

    override fun observePendingTelemetryCount(): Flow<Int> = telemetryDao.observePendingCount()

    override fun observeLastSyncError(): Flow<String?> = telemetryDao.observeLastError()

    override suspend fun syncPendingTelemetry(): ApiResult<Int> {
        val activeSession = sessionDao.getActiveSessionOnce()
            ?: return ApiResult.Error(ApiError.Unknown("No active tracking session to sync."))
        val serverSessionId = activeSession.serverSessionId
            ?: return ApiResult.Error(ApiError.Unknown("Tracking session has not been acknowledged by the server yet."))

        val batch = telemetryDao.getPending(AppConfig.telemetryBatchSize)
        if (batch.isEmpty()) return ApiResult.Success(0)

        TrackingLog.syncStarted(batch.size)
        val ids = batch.map { it.localId }
        telemetryDao.markSyncing(ids)

        val result = safeApiCall {
            trackingApi.submitTelemetryBatch(
                TelemetryBatchRequestDto(
                    sessionId = serverSessionId,
                    points = batch.map { it.toDto() },
                ),
            )
        }

        return when (result) {
            is ApiResult.Success -> {
                telemetryDao.markSynced(ids)
                telemetryDao.deleteSynced()
                TrackingLog.syncSuccess(batch.size)
                ApiResult.Success(batch.size)
            }
            is ApiResult.Error -> {
                telemetryDao.markFailed(ids, result.error.message)
                TrackingLog.syncFailure(result.error.message)
                result
            }
        }
    }

    override suspend fun finalizeStopIfReady(): ApiResult<Unit>? {
        val session = sessionDao.getActiveSessionOnce() ?: return null
        if (TrackingSessionStatus.valueOf(session.status) != TrackingSessionStatus.STOP_REQUESTED) return null

        // Don't finalize while telemetry for THIS session is still pending — the
        // officer's final breadcrumbs must land before we tell the backend to stop.
        val stillPendingForSession = telemetryDao.getPending(1)
            .any { it.trackingSessionLocalId == session.localSessionId }
        if (stillPendingForSession) return null

        val serverSessionId = session.serverSessionId ?: return null
        val result = safeApiCall {
            trackingApi.stopTracking(
                StopTrackingRequestDto(
                    sessionId = serverSessionId,
                    // finalState intentionally null — this app does not yet decide when a
                    // stop corresponds to AT_VISARJAN vs IMMERSION_COMPLETED; see
                    // "Procession lifecycle" in docs/API_CONTRACT.md.
                    finalState = null,
                ),
            )
        }
        return when (result) {
            is ApiResult.Success -> {
                sessionDao.markStopped(session.localSessionId, TrackingSessionStatus.STOPPED.name, System.currentTimeMillis())
                TrackingLog.sessionStopped(serverSessionId)
                ApiResult.Success(Unit)
            }
            is ApiResult.Error -> result
        }
    }
}

private fun TrackingSessionEntity.toDomain() = TrackingSession(
    localSessionId = localSessionId,
    serverSessionId = serverSessionId,
    gpid = gpid,
    assignmentId = assignmentId,
    startedAt = startedAt,
    stoppedAt = stoppedAt,
    status = TrackingSessionStatus.valueOf(status),
    startLocation = GeoPoint.ofOrNull(startLatitude, startLongitude),
)

private fun TelemetryPointEntity.toDto() = TelemetryPointDto(
    clientEventId = clientEventId,
    latitude = latitude,
    longitude = longitude,
    accuracy = accuracyMeters,
    altitude = altitudeMeters,
    speed = speedMetersPerSecond,
    heading = bearingDegrees,
    recordedAt = Instant.ofEpochMilli(recordedAt).toString(),
)
