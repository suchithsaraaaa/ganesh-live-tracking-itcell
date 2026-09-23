package com.ganeshvisarjan.fieldtracker.data.mock

import com.ganeshvisarjan.fieldtracker.core.config.AppConfig
import com.ganeshvisarjan.fieldtracker.core.logging.TrackingLog
import com.ganeshvisarjan.fieldtracker.core.network.ApiResult
import com.ganeshvisarjan.fieldtracker.data.local.dao.TelemetryDao
import com.ganeshvisarjan.fieldtracker.data.local.dao.TrackingSessionDao
import com.ganeshvisarjan.fieldtracker.data.local.entity.TelemetryPointEntity
import com.ganeshvisarjan.fieldtracker.data.local.entity.TrackingSessionEntity
import com.ganeshvisarjan.fieldtracker.domain.model.GeoPoint
import com.ganeshvisarjan.fieldtracker.domain.model.TrackingSession
import com.ganeshvisarjan.fieldtracker.domain.model.TrackingSessionStatus
import com.ganeshvisarjan.fieldtracker.domain.repository.TrackingRepository
import com.ganeshvisarjan.fieldtracker.domain.usecase.GpsQualityValidator
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import java.util.UUID
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Same durable Room queue as the real implementation (Room is local
 * infrastructure, not something mock mode should fake) — only the network leg
 * is simulated, so the offline-queue/sync UI behaves identically to production.
 */
@Singleton
class MockTrackingRepository @Inject constructor(
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
        delay(300)
        val localId = UUID.randomUUID().toString()
        val serverSessionId = "mock-session-${UUID.randomUUID()}"
        val startedAt = System.currentTimeMillis()
        sessionDao.upsert(
            TrackingSessionEntity(
                localId, serverSessionId, gpid, assignmentId, startedAt, null, TrackingSessionStatus.ACTIVE.name,
                startLatitude = officerLocation.latitude, startLongitude = officerLocation.longitude,
            ),
        )
        TrackingLog.sessionStarted(serverSessionId)
        return ApiResult.Success(
            TrackingSession(localId, serverSessionId, gpid, assignmentId, startedAt, null, TrackingSessionStatus.ACTIVE, officerLocation),
        )
    }

    override suspend fun requestStopSession(localSessionId: String) {
        sessionDao.updateStatus(localSessionId, TrackingSessionStatus.STOP_REQUESTED.name)
    }

    override fun observeActiveSession(): Flow<TrackingSession?> = sessionDao.observeActiveSession().map { entity ->
        entity?.let {
            TrackingSession(
                it.localSessionId, it.serverSessionId, it.gpid, it.assignmentId, it.startedAt, it.stoppedAt,
                TrackingSessionStatus.valueOf(it.status), GeoPoint.ofOrNull(it.startLatitude, it.startLongitude),
            )
        }
    }

    override suspend fun getActiveSessionOnce(): TrackingSession? =
        sessionDao.getActiveSessionOnce()?.let {
            TrackingSession(
                it.localSessionId, it.serverSessionId, it.gpid, it.assignmentId, it.startedAt, it.stoppedAt,
                TrackingSessionStatus.valueOf(it.status), GeoPoint.ofOrNull(it.startLatitude, it.startLongitude),
            )
        }

    override suspend fun terminateSessionRemotely(localSessionId: String) {
        sessionDao.markStopped(localSessionId, TrackingSessionStatus.REMOTELY_TERMINATED.name, System.currentTimeMillis())
        TrackingLog.sessionStopped("mock-remotely-terminated-$localSessionId")
    }

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
        val batch = telemetryDao.getPending(AppConfig.telemetryBatchSize)
        if (batch.isEmpty()) return ApiResult.Success(0)
        TrackingLog.syncStarted(batch.size)
        delay(400) // simulate network round trip
        val ids = batch.map { it.localId }
        telemetryDao.markSynced(ids)
        telemetryDao.deleteSynced()
        TrackingLog.syncSuccess(batch.size)
        return ApiResult.Success(batch.size)
    }

    override suspend fun finalizeStopIfReady(): ApiResult<Unit>? {
        val session = sessionDao.getActiveSessionOnce() ?: return null
        if (TrackingSessionStatus.valueOf(session.status) != TrackingSessionStatus.STOP_REQUESTED) return null
        val stillPending = telemetryDao.getPending(1).any { it.trackingSessionLocalId == session.localSessionId }
        if (stillPending) return null
        delay(200)
        sessionDao.markStopped(session.localSessionId, TrackingSessionStatus.STOPPED.name, System.currentTimeMillis())
        TrackingLog.sessionStopped(session.serverSessionId ?: session.localSessionId)
        return ApiResult.Success(Unit)
    }
}
