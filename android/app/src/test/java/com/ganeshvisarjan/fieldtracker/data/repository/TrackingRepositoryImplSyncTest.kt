package com.ganeshvisarjan.fieldtracker.data.repository

import com.ganeshvisarjan.fieldtracker.core.network.ApiResult
import com.ganeshvisarjan.fieldtracker.data.local.dao.TelemetryDao
import com.ganeshvisarjan.fieldtracker.data.local.dao.TrackingSessionDao
import com.ganeshvisarjan.fieldtracker.data.local.entity.TelemetryPointEntity
import com.ganeshvisarjan.fieldtracker.data.local.entity.TrackingSessionEntity
import com.ganeshvisarjan.fieldtracker.data.remote.api.TrackingApi
import com.ganeshvisarjan.fieldtracker.data.remote.dto.StartTrackingResponseDto
import com.ganeshvisarjan.fieldtracker.data.remote.dto.TelemetryBatchResponseDto
import com.ganeshvisarjan.fieldtracker.domain.model.GeoPoint
import com.ganeshvisarjan.fieldtracker.domain.usecase.GpsQualityValidator
import com.google.common.truth.Truth.assertThat
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.mockk
import io.mockk.slot
import kotlinx.coroutines.test.runTest
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Before
import org.junit.Test
import retrofit2.HttpException
import retrofit2.Response

/**
 * Spec section 42 telemetry sync scenarios (A, C, E) against the real
 * [TrackingRepositoryImpl], with Room DAOs and the Retrofit API faked out.
 */
class TrackingRepositoryImplSyncTest {

    private val telemetryDao: TelemetryDao = mockk(relaxUnitFun = true)
    private val sessionDao: TrackingSessionDao = mockk(relaxUnitFun = true)
    private val trackingApi: TrackingApi = mockk()
    private lateinit var repository: TrackingRepositoryImpl

    private val activeSession = TrackingSessionEntity(
        localSessionId = "local-1",
        serverSessionId = "server-1",
        gpid = "HYD-CMRZ-CMNR-0234",
        assignmentId = "assignment-1",
        startedAt = 1000L,
        stoppedAt = null,
        status = "ACTIVE",
        startLatitude = 17.4,
        startLongitude = 78.5,
    )

    @Before
    fun setUp() {
        coEvery { telemetryDao.deleteSynced() } returns 0
        repository = TrackingRepositoryImpl(trackingApi, sessionDao, telemetryDao, GpsQualityValidator())
    }

    private fun fakePoint(id: Long) = TelemetryPointEntity(
        localId = id,
        clientEventId = "event-$id",
        trackingSessionLocalId = "local-1",
        gpid = "HYD-CMRZ-CMNR-0234",
        latitude = 17.4,
        longitude = 78.5,
        accuracyMeters = 8f,
        altitudeMeters = null,
        speedMetersPerSecond = null,
        bearingDegrees = null,
        recordedAt = 1000L,
        createdAt = 1000L,
        syncStatus = "PENDING",
        syncAttempts = 0,
        lastSyncError = null,
    )

    // Scenario A: point generated -> stored -> network available -> uploaded -> synced.
    @Test
    fun `scenario A - pending points upload successfully and get marked synced`() = runTest {
        coEvery { sessionDao.getActiveSessionOnce() } returns activeSession
        coEvery { telemetryDao.getPending(any()) } returns listOf(fakePoint(1), fakePoint(2))
        coEvery { trackingApi.submitTelemetryBatch(any()) } returns
            TelemetryBatchResponseDto(status = "success", received = 2, inserted = 2, duplicatesSkipped = 0)

        val result = repository.syncPendingTelemetry()

        assertThat(result).isInstanceOf(ApiResult.Success::class.java)
        assertThat((result as ApiResult.Success).data).isEqualTo(2)
        coVerify { telemetryDao.markSynced(listOf(1L, 2L)) }
        coVerify { telemetryDao.deleteSynced() }
    }

    // Scenario C: upload times out -> point remains pending (marked FAILED, still queryable as pending) -> retry succeeds.
    @Test
    fun `scenario C - failed upload marks points failed without losing them, then a retry succeeds`() = runTest {
        coEvery { sessionDao.getActiveSessionOnce() } returns activeSession
        coEvery { telemetryDao.getPending(any()) } returns listOf(fakePoint(1))
        coEvery { trackingApi.submitTelemetryBatch(any()) } throws HttpException(Response.error<Any>(500, "".toResponseBody(null)))

        val firstAttempt = repository.syncPendingTelemetry()
        assertThat(firstAttempt).isInstanceOf(ApiResult.Error::class.java)
        coVerify { telemetryDao.markFailed(listOf(1L), any()) }
        coVerify(exactly = 0) { telemetryDao.markSynced(any()) }

        // Retry: same point still comes back from getPending (FAILED is included per the DAO query).
        coEvery { trackingApi.submitTelemetryBatch(any()) } returns
            TelemetryBatchResponseDto(status = "success", received = 1, inserted = 1, duplicatesSkipped = 0)
        val secondAttempt = repository.syncPendingTelemetry()
        assertThat(secondAttempt).isInstanceOf(ApiResult.Success::class.java)
        coVerify { telemetryDao.markSynced(listOf(1L)) }
    }

    // Scenario E: a large backlog syncs in batches, not one point per request.
    @Test
    fun `scenario E - large pending queue is uploaded as a single batch request per sync call`() = runTest {
        val hundredPoints = (1..100L).map { fakePoint(it) }
        coEvery { sessionDao.getActiveSessionOnce() } returns activeSession
        // The DAO itself is responsible for capping to AppConfig.telemetryBatchSize;
        // this test asserts the repository makes exactly ONE network call per sync
        // pass rather than one per point.
        coEvery { telemetryDao.getPending(any()) } returns hundredPoints.take(25)
        coEvery { trackingApi.submitTelemetryBatch(any()) } returns
            TelemetryBatchResponseDto(status = "success", received = 25, inserted = 25, duplicatesSkipped = 0)

        repository.syncPendingTelemetry()

        coVerify(exactly = 1) { trackingApi.submitTelemetryBatch(any()) }
    }

    @Test
    fun `empty queue is a no-op`() = runTest {
        coEvery { sessionDao.getActiveSessionOnce() } returns activeSession
        coEvery { telemetryDao.getPending(any()) } returns emptyList()

        val result = repository.syncPendingTelemetry()

        assertThat(result).isEqualTo(ApiResult.Success(0))
        coVerify(exactly = 0) { trackingApi.submitTelemetryBatch(any()) }
    }

    @Test
    fun `no active session is reported as an error rather than silently dropping data`() = runTest {
        coEvery { sessionDao.getActiveSessionOnce() } returns null

        val result = repository.syncPendingTelemetry()

        assertThat(result).isInstanceOf(ApiResult.Error::class.java)
    }

    // Product-decision change (2026-09-23): there is no client-side proximity
    // check anymore — startSession always sends whatever fresh GPS fix the
    // officer has, regardless of how far it is from the idol's registered
    // origin, and lets the backend be the sole authority on acceptance.
    @Test
    fun `startSession sends the officer's fresh location and device info, with no distance check of any kind`() = runTest {
        val entitySlot = slot<TrackingSessionEntity>()
        coEvery { sessionDao.upsert(capture(entitySlot)) } returns Unit
        coEvery { trackingApi.startTracking(any()) } returns StartTrackingResponseDto(
            id = "server-42",
            assignment = 7,
            gpid = "HYD-CMRZ-CMNR-0234",
            startedAt = "2026-09-23T10:00:00Z",
            status = "ACTIVE",
        )

        // Deliberately a location kilometers from anything idol-related — proves
        // there is nothing in this call path that measures or cares about it.
        val farAwayFix = GeoPoint(28.6139, 77.2090) // New Delhi, nowhere near Hyderabad
        val result = repository.startSession(
            assignmentId = "7",
            gpid = "HYD-CMRZ-CMNR-0234",
            officerLocation = farAwayFix,
            officerAccuracyMeters = 8f,
            deviceInfo = "TestPhone Model X",
        )

        assertThat(result).isInstanceOf(ApiResult.Success::class.java)
        assertThat((result as ApiResult.Success).data.serverSessionId).isEqualTo("server-42")
        coVerify {
            trackingApi.startTracking(
                match { it.latitude == 28.6139 && it.longitude == 77.2090 && it.deviceInfo == "TestPhone Model X" },
            )
        }
        // Test G: the actual start GPS fix is persisted locally, not just sent and discarded.
        assertThat(entitySlot.captured.startLatitude).isEqualTo(28.6139)
        assertThat(entitySlot.captured.startLongitude).isEqualTo(77.2090)
        assertThat(result.data.startLocation).isEqualTo(farAwayFix)
    }

    @Test
    fun `a backend rejection is surfaced as an error, never treated as a started session`() = runTest {
        coEvery { trackingApi.startTracking(any()) } throws
            HttpException(Response.error<Any>(400, "{\"error\":\"Some backend business-rule rejection.\"}".toResponseBody(null)))

        val result = repository.startSession(
            assignmentId = "7",
            gpid = "HYD-CMRZ-CMNR-0234",
            officerLocation = GeoPoint(17.4, 78.6),
            officerAccuracyMeters = 8f,
            deviceInfo = "TestPhone Model X",
        )

        assertThat(result).isInstanceOf(ApiResult.Error::class.java)
        coVerify(exactly = 0) { sessionDao.upsert(any()) }
    }
}
