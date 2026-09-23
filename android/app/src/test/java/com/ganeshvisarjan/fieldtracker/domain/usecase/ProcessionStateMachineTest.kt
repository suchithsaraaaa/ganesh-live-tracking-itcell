package com.ganeshvisarjan.fieldtracker.domain.usecase

import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionEventType
import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionState
import com.google.common.truth.Truth.assertThat
import org.junit.Test

/** Operational lifecycle state transitions test. */
class ProcessionStateMachineTest {

    // --- Valid transitions ---

    @Test
    fun `ASSIGNED to PROCESSION_STARTED via PROCESSION_STARTED event is valid`() {
        assertThat(ProcessionStateMachine.resultingState(ProcessionState.ASSIGNED, ProcessionEventType.PROCESSION_STARTED))
            .isEqualTo(ProcessionState.PROCESSION_STARTED)
    }

    @Test
    fun `ASSIGNED to REACHED_SITE is valid`() {
        assertThat(ProcessionStateMachine.isValidTransition(ProcessionState.ASSIGNED, ProcessionEventType.REACHED_SITE)).isTrue()
    }

    @Test
    fun `REACHED_SITE to PROCESSION_STARTED is valid`() {
        assertThat(ProcessionStateMachine.resultingState(ProcessionState.REACHED_SITE, ProcessionEventType.PROCESSION_STARTED))
            .isEqualTo(ProcessionState.PROCESSION_STARTED)
    }

    @Test
    fun `PROCESSION_STARTED to REACHED_VISARJAN_SITE is valid`() {
        assertThat(ProcessionStateMachine.resultingState(ProcessionState.PROCESSION_STARTED, ProcessionEventType.REACHED_VISARJAN_SITE))
            .isEqualTo(ProcessionState.REACHED_VISARJAN_SITE)
    }

    @Test
    fun `REACHED_VISARJAN_SITE to VISARJAN_DONE is valid`() {
        assertThat(ProcessionStateMachine.resultingState(ProcessionState.REACHED_VISARJAN_SITE, ProcessionEventType.VISARJAN_DONE))
            .isEqualTo(ProcessionState.VISARJAN_DONE)
    }

    @Test
    fun `REACHED_VISARJAN_SITE to VISARJAN_NOT_DONE is valid`() {
        assertThat(ProcessionStateMachine.resultingState(ProcessionState.REACHED_VISARJAN_SITE, ProcessionEventType.VISARJAN_NOT_DONE))
            .isEqualTo(ProcessionState.VISARJAN_NOT_DONE)
    }

    @Test
    fun `VISARJAN_NOT_DONE to SENT_TO_HOLDING is valid`() {
        assertThat(ProcessionStateMachine.resultingState(ProcessionState.VISARJAN_NOT_DONE, ProcessionEventType.SENT_TO_HOLDING))
            .isEqualTo(ProcessionState.SENT_TO_HOLDING)
    }

    @Test
    fun `SENT_TO_HOLDING to RETURNED_TO_ORIGIN is valid`() {
        assertThat(ProcessionStateMachine.resultingState(ProcessionState.SENT_TO_HOLDING, ProcessionEventType.RETURNED_TO_ORIGIN))
            .isEqualTo(ProcessionState.RETURNED_TO_ORIGIN)
    }

    // --- Invalid transitions ---

    @Test
    fun `PROCESSION_STARTED to VISARJAN_DONE directly is rejected`() {
        assertThat(ProcessionStateMachine.isValidTransition(ProcessionState.PROCESSION_STARTED, ProcessionEventType.VISARJAN_DONE)).isFalse()
    }

    @Test
    fun `RETURNED_TO_ORIGIN has no further valid events`() {
        assertThat(ProcessionStateMachine.availableEvents(ProcessionState.RETURNED_TO_ORIGIN)).isEmpty()
        assertThat(ProcessionStateMachine.isTerminal(ProcessionState.RETURNED_TO_ORIGIN)).isTrue()
    }

    @Test
    fun `VISARJAN_DONE has no further valid events`() {
        assertThat(ProcessionStateMachine.availableEvents(ProcessionState.VISARJAN_DONE)).isEmpty()
        assertThat(ProcessionStateMachine.isTerminal(ProcessionState.VISARJAN_DONE)).isTrue()
    }

    // --- GPS tracking continuity ---

    @Test
    fun `gps tracking continues through the active lifecycle`() {
        assertThat(ProcessionStateMachine.shouldContinueGpsTracking(ProcessionState.PROCESSION_STARTED)).isTrue()
        assertThat(ProcessionStateMachine.shouldContinueGpsTracking(ProcessionState.REACHED_VISARJAN_SITE)).isTrue()
        assertThat(ProcessionStateMachine.shouldContinueGpsTracking(ProcessionState.VISARJAN_NOT_DONE)).isTrue()
        assertThat(ProcessionStateMachine.shouldContinueGpsTracking(ProcessionState.SENT_TO_HOLDING)).isTrue()
    }

    @Test
    fun `gps tracking does not continue for terminal or pre-start states`() {
        assertThat(ProcessionStateMachine.shouldContinueGpsTracking(ProcessionState.ASSIGNED)).isFalse()
        assertThat(ProcessionStateMachine.shouldContinueGpsTracking(ProcessionState.REACHED_SITE)).isFalse()
        assertThat(ProcessionStateMachine.shouldContinueGpsTracking(ProcessionState.VISARJAN_DONE)).isFalse()
        assertThat(ProcessionStateMachine.shouldContinueGpsTracking(ProcessionState.RETURNED_TO_ORIGIN)).isFalse()
    }
}
