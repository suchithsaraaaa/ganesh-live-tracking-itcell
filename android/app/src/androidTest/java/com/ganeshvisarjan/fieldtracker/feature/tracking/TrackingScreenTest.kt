package com.ganeshvisarjan.fieldtracker.feature.tracking

import androidx.compose.ui.test.assertTextEquals
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.ganeshvisarjan.fieldtracker.core.network.NetworkMonitor
import com.ganeshvisarjan.fieldtracker.core.network.NetworkState
import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionEventRecord
import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionEventType
import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionState
import com.ganeshvisarjan.fieldtracker.domain.model.SyncStatus
import com.ganeshvisarjan.fieldtracker.domain.model.TrackingSession
import com.ganeshvisarjan.fieldtracker.domain.model.TrackingSessionStatus
import com.ganeshvisarjan.fieldtracker.domain.repository.AssignmentRepository
import com.ganeshvisarjan.fieldtracker.domain.repository.ProcessionRepository
import com.ganeshvisarjan.fieldtracker.domain.repository.TrackingRepository
import com.ganeshvisarjan.fieldtracker.domain.usecase.ProcessionStateMachine
import com.ganeshvisarjan.fieldtracker.service.TrackingServiceState
import com.ganeshvisarjan.fieldtracker.worker.SyncScheduler
import io.mockk.coEvery
import io.mockk.every
import io.mockk.mockk
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.flowOf
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Tests the actual state/action behavior for every reachable [ProcessionState]:
 * the correct status text is shown, and exactly the buttons
 * [ProcessionStateMachine.availableEvents] allows for that state are offered —
 * not just "some text exists somewhere". [TrackingViewModel] is constructed
 * directly (bypassing `hiltViewModel()`) against faked repositories.
 */
@RunWith(AndroidJUnit4::class)
class TrackingScreenTest {

    @get:Rule
    val composeRule = createComposeRule()

    private val session = TrackingSession(
        localSessionId = "local-1",
        serverSessionId = "server-1",
        gpid = "HYD-CMRZ-CMNR-0234",
        assignmentId = "assignment-1",
        startedAt = 1_000L,
        stoppedAt = null,
        status = TrackingSessionStatus.ACTIVE,
    )

    private fun buildViewModel(state: ProcessionState): TrackingViewModel {
        val trackingRepository: TrackingRepository = mockk {
            every { observeActiveSession() } returns flowOf(session)
            every { observePendingTelemetryCount() } returns flowOf(0)
            every { observeLastSyncError() } returns flowOf(null)
        }
        val processionRepository: ProcessionRepository = mockk {
            every { observeState(session.gpid) } returns flowOf(state)
            every { observeTimeline(session.gpid) } returns flowOf(
                listOf(
                    ProcessionEventRecord(
                        localId = 1, clientEventId = "e1", gpid = session.gpid, assignmentId = session.assignmentId,
                        trackingSessionLocalId = session.localSessionId, eventType = ProcessionEventType.PROCESSION_STARTED,
                        occurredAt = 1_000L, latitude = 17.36, longitude = 78.47,
                        syncStatus = SyncStatus.SYNCED, syncAttempts = 0, lastSyncError = null,
                    ),
                ),
            )
            every { observePendingEventCount() } returns flowOf(0)
        }
        val assignmentRepository: AssignmentRepository = mockk(relaxed = true)
        val networkMonitor: NetworkMonitor = mockk {
            every { state } returns MutableStateFlow(NetworkState.ONLINE)
        }
        return TrackingViewModel(
            context = ApplicationProvider.getApplicationContext(),
            trackingRepository = trackingRepository,
            processionRepository = processionRepository,
            assignmentRepository = assignmentRepository,
            networkMonitor = networkMonitor,
            serviceState = TrackingServiceState(),
            syncScheduler = mockk(relaxed = true),
        )
    }

    private fun assertStateAndActions(state: ProcessionState) {
        composeRule.setContent {
            TrackingScreen(viewModel = buildViewModel(state))
        }
        composeRule.waitForIdle()

        composeRule.onNodeWithTag("procession_state_header").assertTextEquals(state.name.replace('_', ' '))

        val expectedActions = ProcessionStateMachine.availableEvents(state)
        expectedActions.forEach { action ->
            val label = when (action) {
                ProcessionEventType.PROCESSION_STARTED -> "PROCESSION STARTED"
                ProcessionEventType.MOVING -> "MOVING"
                ProcessionEventType.REACHED_VISARJAN_AREA -> "REACHED VISARJAN AREA"
                ProcessionEventType.VISARJAN_DONE -> "VISARJAN DONE"
                ProcessionEventType.HOLDING -> "PUT IN HOLDING"
                ProcessionEventType.RETURNING_TO_PANDAL -> "RETURNING TO PANDAL"
                ProcessionEventType.RETURNED_TO_PANDAL -> "RETURNED TO PANDAL"
            }
            composeRule.onNodeWithText(label).assertExists()
        }

        // Always offered regardless of state.
        composeRule.onNodeWithText("STOP TRACKING").assertExists()
    }

    @Test
    fun processionStarted_offersOnlyMoving() = assertStateAndActions(ProcessionState.PROCESSION_STARTED)

    @Test
    fun moving_offersOnlyReachedVisarjanArea() = assertStateAndActions(ProcessionState.MOVING)

    @Test
    fun reachedVisarjanArea_offersVisarjanDoneAndHolding() = assertStateAndActions(ProcessionState.REACHED_VISARJAN_AREA)

    @Test
    fun holding_offersOnlyReturningToPandal() = assertStateAndActions(ProcessionState.HOLDING)

    @Test
    fun returningToPandal_offersOnlyReturnedToPandal() = assertStateAndActions(ProcessionState.RETURNING_TO_PANDAL)

    @Test
    fun returnedToPandal_isTerminal_offersNoFurtherActions() {
        composeRule.setContent {
            TrackingScreen(viewModel = buildViewModel(ProcessionState.RETURNED_TO_PANDAL))
        }
        composeRule.waitForIdle()

        composeRule.onNodeWithTag("procession_state_header").assertTextEquals("RETURNED TO PANDAL")
        // Still offered — stopping tracking is independent of procession state (spec section 25).
        composeRule.onNodeWithText("STOP TRACKING").assertExists()
    }

    @Test
    fun visarjanDone_isTerminal_offersNoFurtherActions() {
        composeRule.setContent {
            TrackingScreen(viewModel = buildViewModel(ProcessionState.VISARJAN_DONE))
        }
        composeRule.waitForIdle()

        composeRule.onNodeWithTag("procession_state_header").assertTextEquals("VISARJAN DONE")
        composeRule.onNodeWithText("STOP TRACKING").assertExists()
    }
}
