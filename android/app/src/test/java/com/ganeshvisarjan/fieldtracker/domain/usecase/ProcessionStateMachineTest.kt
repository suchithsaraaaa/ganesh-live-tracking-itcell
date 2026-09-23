package com.ganeshvisarjan.fieldtracker.domain.usecase

import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionEventType
import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionState
import com.google.common.truth.Truth.assertThat
import org.junit.Test

/** Spec section 39 — every valid transition and a representative set of illegal ones. */
class ProcessionStateMachineTest {

    // --- Valid transitions (spec section 13) ---

    @Test
    fun `ASSIGNED to PROCESSION_STARTED via PROCESSION_STARTED event is valid`() {
        assertThat(ProcessionStateMachine.resultingState(ProcessionState.ASSIGNED, ProcessionEventType.PROCESSION_STARTED))
            .isEqualTo(ProcessionState.PROCESSION_STARTED)
    }

    @Test
    fun `AT_IDOL to PROCESSION_STARTED is valid`() {
        assertThat(ProcessionStateMachine.isValidTransition(ProcessionState.AT_IDOL, ProcessionEventType.PROCESSION_STARTED)).isTrue()
    }

    @Test
    fun `PROCESSION_STARTED to MOVING is valid`() {
        assertThat(ProcessionStateMachine.resultingState(ProcessionState.PROCESSION_STARTED, ProcessionEventType.MOVING))
            .isEqualTo(ProcessionState.MOVING)
    }

    @Test
    fun `MOVING to REACHED_VISARJAN_AREA is valid`() {
        assertThat(ProcessionStateMachine.resultingState(ProcessionState.MOVING, ProcessionEventType.REACHED_VISARJAN_AREA))
            .isEqualTo(ProcessionState.REACHED_VISARJAN_AREA)
    }

    @Test
    fun `REACHED_VISARJAN_AREA to VISARJAN_DONE is valid`() {
        assertThat(ProcessionStateMachine.resultingState(ProcessionState.REACHED_VISARJAN_AREA, ProcessionEventType.VISARJAN_DONE))
            .isEqualTo(ProcessionState.VISARJAN_DONE)
    }

    @Test
    fun `REACHED_VISARJAN_AREA to HOLDING is valid`() {
        assertThat(ProcessionStateMachine.resultingState(ProcessionState.REACHED_VISARJAN_AREA, ProcessionEventType.HOLDING))
            .isEqualTo(ProcessionState.HOLDING)
    }

    @Test
    fun `HOLDING to RETURNING_TO_PANDAL is valid`() {
        assertThat(ProcessionStateMachine.resultingState(ProcessionState.HOLDING, ProcessionEventType.RETURNING_TO_PANDAL))
            .isEqualTo(ProcessionState.RETURNING_TO_PANDAL)
    }

    @Test
    fun `RETURNING_TO_PANDAL to RETURNED_TO_PANDAL is valid`() {
        assertThat(ProcessionStateMachine.resultingState(ProcessionState.RETURNING_TO_PANDAL, ProcessionEventType.RETURNED_TO_PANDAL))
            .isEqualTo(ProcessionState.RETURNED_TO_PANDAL)
    }

    // --- Invalid transitions (spec section 39) ---

    @Test
    fun `PROCESSION_STARTED to VISARJAN_DONE is rejected`() {
        assertThat(ProcessionStateMachine.isValidTransition(ProcessionState.PROCESSION_STARTED, ProcessionEventType.VISARJAN_DONE)).isFalse()
    }

    @Test
    fun `PROCESSION_STARTED to REACHED_VISARJAN_AREA is rejected without MOVING first`() {
        assertThat(ProcessionStateMachine.isValidTransition(ProcessionState.PROCESSION_STARTED, ProcessionEventType.REACHED_VISARJAN_AREA)).isFalse()
    }

    @Test
    fun `HOLDING to VISARJAN_DONE is rejected`() {
        assertThat(ProcessionStateMachine.isValidTransition(ProcessionState.HOLDING, ProcessionEventType.VISARJAN_DONE)).isFalse()
    }

    @Test
    fun `RETURNING_TO_PANDAL to VISARJAN_DONE is rejected`() {
        assertThat(ProcessionStateMachine.isValidTransition(ProcessionState.RETURNING_TO_PANDAL, ProcessionEventType.VISARJAN_DONE)).isFalse()
    }

    @Test
    fun `RETURNED_TO_PANDAL has no further valid events`() {
        assertThat(ProcessionStateMachine.availableEvents(ProcessionState.RETURNED_TO_PANDAL)).isEmpty()
        assertThat(ProcessionStateMachine.isTerminal(ProcessionState.RETURNED_TO_PANDAL)).isTrue()
    }

    @Test
    fun `VISARJAN_DONE has no further valid events`() {
        assertThat(ProcessionStateMachine.availableEvents(ProcessionState.VISARJAN_DONE)).isEmpty()
        assertThat(ProcessionStateMachine.isTerminal(ProcessionState.VISARJAN_DONE)).isTrue()
    }

    @Test
    fun `ASSIGNED to MOVING directly is rejected`() {
        assertThat(ProcessionStateMachine.isValidTransition(ProcessionState.ASSIGNED, ProcessionEventType.MOVING)).isFalse()
    }

    // --- GPS tracking continuity (spec section 42) ---

    @Test
    fun `gps tracking continues through the active lifecycle`() {
        assertThat(ProcessionStateMachine.shouldContinueGpsTracking(ProcessionState.PROCESSION_STARTED)).isTrue()
        assertThat(ProcessionStateMachine.shouldContinueGpsTracking(ProcessionState.MOVING)).isTrue()
        assertThat(ProcessionStateMachine.shouldContinueGpsTracking(ProcessionState.REACHED_VISARJAN_AREA)).isTrue()
        assertThat(ProcessionStateMachine.shouldContinueGpsTracking(ProcessionState.HOLDING)).isTrue()
        assertThat(ProcessionStateMachine.shouldContinueGpsTracking(ProcessionState.RETURNING_TO_PANDAL)).isTrue()
    }

    @Test
    fun `gps tracking does not continue for terminal or pre-start states`() {
        assertThat(ProcessionStateMachine.shouldContinueGpsTracking(ProcessionState.ASSIGNED)).isFalse()
        assertThat(ProcessionStateMachine.shouldContinueGpsTracking(ProcessionState.AT_IDOL)).isFalse()
        assertThat(ProcessionStateMachine.shouldContinueGpsTracking(ProcessionState.VISARJAN_DONE)).isFalse()
        assertThat(ProcessionStateMachine.shouldContinueGpsTracking(ProcessionState.RETURNED_TO_PANDAL)).isFalse()
    }
}
