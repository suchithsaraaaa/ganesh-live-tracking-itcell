package com.ganeshvisarjan.fieldtracker.domain.usecase

import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionEventType
import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionState
import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionState.ASSIGNED
import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionState.REACHED_SITE
import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionState.PROCESSION_STARTED
import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionState.REACHED_VISARJAN_SITE
import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionState.VISARJAN_DONE
import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionState.VISARJAN_NOT_DONE
import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionState.SENT_TO_HOLDING
import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionState.RETURNED_TO_ORIGIN

/**
 * Single source of truth for which [ProcessionEventType] is legal from which
 * [ProcessionState]. Every layer (ViewModel, Repository, Worker) must route
 * through this object instead of re-deriving the rule.
 *
 * Implements the required operational lifecycle:
 * ASSIGNED -> REACHED_SITE -> PROCESSION_STARTED -> REACHED_VISARJAN_SITE ->
 * (VISARJAN_DONE | VISARJAN_NOT_DONE -> SENT_TO_HOLDING -> RETURNED_TO_ORIGIN)
 */
object ProcessionStateMachine {

    private val transitions: Map<ProcessionState, Map<ProcessionEventType, ProcessionState>> = mapOf(
        ASSIGNED to mapOf(
            ProcessionEventType.REACHED_SITE to REACHED_SITE,
            ProcessionEventType.PROCESSION_STARTED to PROCESSION_STARTED,
        ),
        REACHED_SITE to mapOf(
            ProcessionEventType.PROCESSION_STARTED to PROCESSION_STARTED,
        ),
        PROCESSION_STARTED to mapOf(
            ProcessionEventType.REACHED_VISARJAN_SITE to REACHED_VISARJAN_SITE,
        ),
        REACHED_VISARJAN_SITE to mapOf(
            ProcessionEventType.VISARJAN_DONE to VISARJAN_DONE,
            ProcessionEventType.VISARJAN_NOT_DONE to VISARJAN_NOT_DONE,
        ),
        VISARJAN_NOT_DONE to mapOf(
            ProcessionEventType.SENT_TO_HOLDING to SENT_TO_HOLDING,
            ProcessionEventType.VISARJAN_DONE to VISARJAN_DONE,
        ),
        SENT_TO_HOLDING to mapOf(
            ProcessionEventType.RETURNED_TO_ORIGIN to RETURNED_TO_ORIGIN,
            ProcessionEventType.REACHED_VISARJAN_SITE to REACHED_VISARJAN_SITE,
        ),
        RETURNED_TO_ORIGIN to emptyMap(),
        VISARJAN_DONE to emptyMap(),
    )

    /** Events a field officer may legally trigger from [state] right now. */
    fun availableEvents(state: ProcessionState): Set<ProcessionEventType> =
        transitions[state]?.keys ?: emptySet()

    /** The state [event] would move [state] into, or null if that transition is illegal. */
    fun resultingState(state: ProcessionState, event: ProcessionEventType): ProcessionState? =
        transitions[state]?.get(event)

    fun isValidTransition(state: ProcessionState, event: ProcessionEventType): Boolean =
        resultingState(state, event) != null

    /** True once no further officer-triggered events are possible from [state]. */
    fun isTerminal(state: ProcessionState): Boolean =
        transitions[state]?.isEmpty() == true

    /** True while GPS telemetry should keep being collected for this state. */
    fun shouldContinueGpsTracking(state: ProcessionState): Boolean = when (state) {
        ASSIGNED, REACHED_SITE -> false
        PROCESSION_STARTED, REACHED_VISARJAN_SITE, VISARJAN_NOT_DONE, SENT_TO_HOLDING -> true
        RETURNED_TO_ORIGIN, VISARJAN_DONE -> false
    }

    /** Ordered list used to render the timeline UI, independent of which ones actually occurred. */
    val timelineOrder: List<ProcessionState> = listOf(
        REACHED_SITE, PROCESSION_STARTED, REACHED_VISARJAN_SITE, VISARJAN_DONE, VISARJAN_NOT_DONE, SENT_TO_HOLDING, RETURNED_TO_ORIGIN,
    )
}
