package com.ganeshvisarjan.fieldtracker.data.repository

import com.ganeshvisarjan.fieldtracker.data.local.dao.TelemetryDao
import com.ganeshvisarjan.fieldtracker.data.local.dao.TrackingSessionDao
import com.ganeshvisarjan.fieldtracker.data.local.entity.TrackingSessionEntity
import com.ganeshvisarjan.fieldtracker.data.remote.api.TrackingApi
import com.ganeshvisarjan.fieldtracker.domain.model.GeoPoint
import com.ganeshvisarjan.fieldtracker.domain.model.TrackingSessionStatus
import com.ganeshvisarjan.fieldtracker.domain.usecase.GpsQualityValidator
import com.ganeshvisarjan.fieldtracker.domain.usecase.ServiceRestartDecision
import com.google.common.truth.Truth.assertThat
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.mockk
import io.mockk.slot
import kotlinx.coroutines.test.runTest
import org.junit.Before
import org.junit.Test

class RemoteAdminTerminationTest {

    private val telemetryDao: TelemetryDao = mockk(relaxUnitFun = true)
    private val sessionDao: TrackingSessionDao = mockk(relaxUnitFun = true)
    private val trackingApi: TrackingApi = mockk()
    private lateinit var repository: TrackingRepositoryImpl

    private val activeSession = TrackingSessionEntity(
        localSessionId = "local-session-1",
        serverSessionId = "server-session-1",
        gpid = "HYD-CMRZ-CHGT-1164",
        assignmentId = "assign-101",
        startedAt = 1000L,
        stoppedAt = null,
        status = "ACTIVE",
        startLatitude = 17.3850,
        startLongitude = 78.4867,
    )

    private val remotelyTerminatedSession = TrackingSessionEntity(
        localSessionId = "local-session-1",
        serverSessionId = "server-session-1",
        gpid = "HYD-CMRZ-CHGT-1164",
        assignmentId = "assign-101",
        startedAt = 1000L,
        stoppedAt = 2000L,
        status = TrackingSessionStatus.REMOTELY_TERMINATED.name,
        startLatitude = 17.3850,
        startLongitude = 78.4867,
    )

    @Before
    fun setUp() {
        repository = TrackingRepositoryImpl(trackingApi, sessionDao, telemetryDao, GpsQualityValidator())
    }

    @Test
    fun `getActiveSessionOnce returns active domain session when active in Room`() = runTest {
        coEvery { sessionDao.getActiveSessionOnce() } returns activeSession

        val session = repository.getActiveSessionOnce()

        assertThat(session).isNotNull()
        assertThat(session?.localSessionId).isEqualTo("local-session-1")
        assertThat(session?.status).isEqualTo(TrackingSessionStatus.ACTIVE)
        assertThat(session?.gpid).isEqualTo("HYD-CMRZ-CHGT-1164")
    }

    @Test
    fun `getActiveSessionOnce returns null when Room returns null (e_g_ session remotely terminated)`() = runTest {
        coEvery { sessionDao.getActiveSessionOnce() } returns null

        val session = repository.getActiveSessionOnce()

        assertThat(session).isNull()
    }

    @Test
    fun `terminateSessionRemotely marks session REMOTELY_TERMINATED with current timestamp`() = runTest {
        val capturedStatus = slot<String>()
        val capturedStoppedAt = slot<Long>()

        coEvery {
            sessionDao.markStopped(
                localId = "local-session-1",
                status = capture(capturedStatus),
                stoppedAt = capture(capturedStoppedAt),
            )
        } returns Unit

        repository.terminateSessionRemotely("local-session-1")

        coVerify(exactly = 1) {
            sessionDao.markStopped("local-session-1", TrackingSessionStatus.REMOTELY_TERMINATED.name, any())
        }
        assertThat(capturedStatus.captured).isEqualTo(TrackingSessionStatus.REMOTELY_TERMINATED.name)
        assertThat(capturedStoppedAt.captured).isGreaterThan(0L)
    }

    @Test
    fun `recordTelemetryPoint rejects telemetry and does not insert when session is REMOTELY_TERMINATED`() = runTest {
        coEvery { sessionDao.getById("local-session-1") } returns remotelyTerminatedSession

        val recorded = repository.recordTelemetryPoint(
            sessionLocalId = "local-session-1",
            gpid = "HYD-CMRZ-CHGT-1164",
            location = GeoPoint(17.3851, 78.4868),
            accuracyMeters = 5.0f,
            altitudeMeters = 500.0,
            speedMetersPerSecond = 1.2f,
            bearingDegrees = 90.0f,
            recordedAt = 2500L,
        )

        assertThat(recorded).isFalse()
        coVerify(exactly = 0) { telemetryDao.insert(any()) }
    }

    @Test
    fun `recordTelemetryPoint accepts and stores telemetry when session is ACTIVE`() = runTest {
        coEvery { sessionDao.getById("local-session-1") } returns activeSession
        coEvery { telemetryDao.insert(any()) } returns 42L

        val recorded = repository.recordTelemetryPoint(
            sessionLocalId = "local-session-1",
            gpid = "HYD-CMRZ-CHGT-1164",
            location = GeoPoint(17.3851, 78.4868),
            accuracyMeters = 5.0f,
            altitudeMeters = 500.0,
            speedMetersPerSecond = 1.2f,
            bearingDegrees = 90.0f,
            recordedAt = 2500L,
        )

        assertThat(recorded).isTrue()
        coVerify(exactly = 1) { telemetryDao.insert(any()) }
    }

    @Test
    fun `ServiceRestartDecision returns DoNothing for REMOTELY_TERMINATED session`() {
        val domainSession = com.ganeshvisarjan.fieldtracker.domain.model.TrackingSession(
            localSessionId = "local-session-1",
            serverSessionId = "server-session-1",
            gpid = "HYD-CMRZ-CHGT-1164",
            assignmentId = "assign-101",
            startedAt = 1000L,
            stoppedAt = 2000L,
            status = TrackingSessionStatus.REMOTELY_TERMINATED,
        )

        val decision = ServiceRestartDecision.decide(domainSession)

        assertThat(decision).isEqualTo(ServiceRestartDecision.Action.DoNothing)
    }

    @Test
    fun `repeated remote termination is safe and idempotent`() = runTest {
        coEvery { sessionDao.markStopped(any(), any(), any()) } returns Unit

        repository.terminateSessionRemotely("local-session-1")
        repository.terminateSessionRemotely("local-session-1")

        coVerify(exactly = 2) {
            sessionDao.markStopped("local-session-1", TrackingSessionStatus.REMOTELY_TERMINATED.name, any())
        }
    }
}
