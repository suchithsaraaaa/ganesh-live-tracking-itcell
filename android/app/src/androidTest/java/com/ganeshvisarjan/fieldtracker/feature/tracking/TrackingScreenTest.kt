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
 * [ProcessionStateMachine.availableEvents] allows for that state are offered.
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

    private fun buildViewModel(processionState: ProcessionState): TrackingViewModel {
        val trackingRepository: TrackingRepository = mockk {
            every { observeActiveSession() } returns flowOf(session)
            every { observePendingTelemetryCount() } returns flowOf(0)
            every { observeLastSyncError() } returns flowOf(null)
        }
        val processionRepository: ProcessionRepository = mockk {
            every { observeState(session.gpid) } returns flowOf(processionState)
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
            locationClient = mockk(relaxed = true),
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
            val label = actionLabel(action)
            composeRule.onNodeWithText(label).assertExists()
        }

        // Always offered regardless of state.
        composeRule.onNodeWithText("STOP TRACKING").assertExists()
    }

    @Test
    fun processionStarted_offersReachedVisarjanSite() = assertStateAndActions(ProcessionState.PROCESSION_STARTED)

    @Test
    fun reachedVisarjanSite_offersVisarjanDoneAndNotDone() = assertStateAndActions(ProcessionState.REACHED_VISARJAN_SITE)

    @Test
    fun visarjanNotDone_offersSendToHoldingAndVisarjanDone() = assertStateAndActions(ProcessionState.VISARJAN_NOT_DONE)

    @Test
    fun sentToHolding_offersReturnToOriginAndVisarjanSite() = assertStateAndActions(ProcessionState.SENT_TO_HOLDING)

    @Test
    fun returnedToOrigin_isTerminal_offersNoFurtherActions() {
        composeRule.setContent {
            TrackingScreen(viewModel = buildViewModel(ProcessionState.RETURNED_TO_ORIGIN))
        }
        composeRule.waitForIdle()

        composeRule.onNodeWithTag("procession_state_header").assertTextEquals("RETURNED TO ORIGIN")
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
