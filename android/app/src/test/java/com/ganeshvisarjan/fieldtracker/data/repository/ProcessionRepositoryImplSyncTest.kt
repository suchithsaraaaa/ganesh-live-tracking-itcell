package com.ganeshvisarjan.fieldtracker.data.repository

import com.ganeshvisarjan.fieldtracker.core.network.ApiResult
import com.ganeshvisarjan.fieldtracker.data.local.dao.ProcessionEventDao
import com.ganeshvisarjan.fieldtracker.data.local.entity.ProcessionEventEntity
import com.ganeshvisarjan.fieldtracker.data.remote.api.ProcessionApi
import com.ganeshvisarjan.fieldtracker.data.remote.dto.ProcessionStateResponseDto
import com.google.common.truth.Truth.assertThat
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.coVerifyOrder
import io.mockk.mockk
import kotlinx.coroutines.test.runTest
import org.junit.Before
import org.junit.Test

/** Spec section 24 — chronological order must be preserved when syncing queued offline events. */
class ProcessionRepositoryImplSyncTest {

    private val dao: ProcessionEventDao = mockk(relaxUnitFun = true)
    private val api: ProcessionApi = mockk()
    private lateinit var repository: ProcessionRepositoryImpl

    @Before
    fun setUp() {
        repository = ProcessionRepositoryImpl(api, dao)
    }

    private fun entity(id: Long, type: String, occurredAt: Long) = ProcessionEventEntity(
        localId = id,
        clientEventId = "event-$id",
        gpid = "HYD-CMRZ-CMNR-0234",
        assignmentId = "assignment-1",
        trackingSessionLocalId = "session-1",
        eventType = type,
        occurredAt = occurredAt,
        latitude = 17.4,
        longitude = 78.5,
        syncStatus = "PENDING",
        syncAttempts = 0,
        lastSyncError = null,
    )

    @Test
    fun `events are uploaded to the backend in chronological order`() = runTest {
        val ordered = listOf(
            entity(1, "PROCESSION_STARTED", 1000),
            entity(2, "MOVING", 2000),
            entity(3, "REACHED_VISARJAN_AREA", 3000),
        )
        coEvery { dao.getPendingChronological() } returns ordered
        coEvery { api.submitEvent(any()) } returns ProcessionStateResponseDto(gpid = "HYD-CMRZ-CMNR-0234", state = "MOVING")

        repository.syncPendingEvents()

        coVerifyOrder {
            api.submitEvent(match { it.eventType == "PROCESSION_STARTED" })
            api.submitEvent(match { it.eventType == "MOVING" })
            api.submitEvent(match { it.eventType == "REACHED_VISARJAN_AREA" })
        }
    }

    @Test
    fun `a failure stops the batch rather than uploading a later event out of order`() = runTest {
        val ordered = listOf(
            entity(1, "PROCESSION_STARTED", 1000),
            entity(2, "MOVING", 2000),
        )
        coEvery { dao.getPendingChronological() } returns ordered
        coEvery { api.submitEvent(match { it.eventType == "PROCESSION_STARTED" }) } returns
            ProcessionStateResponseDto(gpid = "g", state = "PROCESSION_STARTED")
        coEvery { api.submitEvent(match { it.eventType == "MOVING" }) } throws RuntimeException("network down")

        val result = repository.syncPendingEvents()

        assertThat(result).isInstanceOf(ApiResult.Success::class.java) // 1 uploaded before the failure
        coVerify(exactly = 1) { api.submitEvent(match { it.eventType == "MOVING" }) } // attempted, not skipped
        coVerify { dao.markFailed(2L, any()) }
        coVerify(exactly = 0) { dao.markSynced(2L) }
    }

    @Test
    fun `retrying the same local event reuses its client_event_id`() = runTest {
        // The event row's clientEventId never changes across syncPendingEvents() calls —
        // this is what lets the backend deduplicate a retried submission.
        val entity = entity(1, "MOVING", 1000)
        coEvery { dao.getPendingChronological() } returns listOf(entity)
        coEvery { api.submitEvent(any()) } throws RuntimeException("timeout")

        repository.syncPendingEvents()
        repository.syncPendingEvents()

        coVerify(exactly = 2) { api.submitEvent(match { it.clientEventId == "event-1" }) }
    }
}
