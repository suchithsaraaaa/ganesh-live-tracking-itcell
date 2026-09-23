package com.ganeshvisarjan.fieldtracker.data.local

import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.ganeshvisarjan.fieldtracker.data.local.entity.ProcessionEventEntity
import com.google.common.truth.Truth.assertThat
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import org.junit.After
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

/** Spec section 24 — offline events must sync in chronological (occurred_at) order, not upload order. */
@RunWith(AndroidJUnit4::class)
class ProcessionEventDaoTest {

    private lateinit var db: AppDatabase
    private lateinit var dao: com.ganeshvisarjan.fieldtracker.data.local.dao.ProcessionEventDao

    @Before
    fun setUp() {
        db = Room.inMemoryDatabaseBuilder(ApplicationProvider.getApplicationContext(), AppDatabase::class.java)
            .allowMainThreadQueries()
            .build()
        dao = db.processionEventDao()
    }

    @After
    fun tearDown() {
        db.close()
    }

    private fun event(clientEventId: String, type: String, occurredAt: Long) = ProcessionEventEntity(
        clientEventId = clientEventId,
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
    fun pendingEventsComeBackInChronologicalOrder_regardlessOfInsertOrder() = runBlocking {
        // Inserted out of order — as would happen if the officer went offline and
        // the events queued up while network was unavailable, then synced later.
        dao.insert(event("reached", "REACHED_VISARJAN_AREA", 3000))
        dao.insert(event("started", "PROCESSION_STARTED", 1000))
        dao.insert(event("moving", "MOVING", 2000))

        val pending = dao.getPendingChronological()
        assertThat(pending.map { it.eventType }).isEqualTo(listOf("PROCESSION_STARTED", "MOVING", "REACHED_VISARJAN_AREA"))
    }

    @Test
    fun duplicateClientEventIdIsIgnored() = runBlocking {
        dao.insert(event("dup", "MOVING", 1000))
        dao.insert(event("dup", "HOLDING", 2000)) // retry of the same local event must not create a second row
        assertThat(dao.getPendingChronological()).hasSize(1)
        assertThat(dao.getPendingChronological().first().eventType).isEqualTo("MOVING")
    }

    @Test
    fun markSyncedRemovesEventFromPendingQueue() = runBlocking {
        dao.insert(event("a", "PROCESSION_STARTED", 1000))
        val id = dao.getPendingChronological().first().localId

        dao.markSynced(id)

        assertThat(dao.observePendingCount().first()).isEqualTo(0)
    }

    @Test
    fun timelineForGpidIsOrderedByOccurredAt() = runBlocking {
        dao.insert(event("b", "MOVING", 2000))
        dao.insert(event("a", "PROCESSION_STARTED", 1000))

        val timeline = dao.observeTimeline("HYD-CMRZ-CMNR-0234").first()
        assertThat(timeline.map { it.eventType }).isEqualTo(listOf("PROCESSION_STARTED", "MOVING"))
    }
}
