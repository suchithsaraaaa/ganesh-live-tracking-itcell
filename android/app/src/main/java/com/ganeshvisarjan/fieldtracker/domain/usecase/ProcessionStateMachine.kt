package com.ganeshvisarjan.fieldtracker.domain.usecase

import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionEventType
import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionState
import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionState.ASSIGNED
import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionState.AT_IDOL
import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionState.HOLDING
import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionState.MOVING
import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionState.PROCESSION_STARTED
import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionState.REACHED_VISARJAN_AREA
import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionState.RETURNED_TO_PANDAL
import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionState.RETURNING_TO_PANDAL
import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionState.VISARJAN_DONE

/**
 * Single source of truth for which [ProcessionEventType] is legal from which
 * [ProcessionState]. Every layer (ViewModel, Repository, Worker) must route
 * through this object instead of re-deriving the rule — see spec section 44.
 *
 * The backend is the actual authority; this table exists so the Android UI can
 * (a) grey out actions that are obviously illegal before making a network call,
 * and (b) be exhaustively unit-tested (see ProcessionStateMachineTest). A
 * successful backend response is what actually advances [ProcessionState] —
 * this table never advances state on its own.
 */
object ProcessionStateMachine {

    private val transitions: Map<ProcessionState, Map<ProcessionEventType, ProcessionState>> = mapOf(
        ASSIGNED to mapOf(
            ProcessionEventType.PROCESSION_STARTED to PROCESSION_STARTED,
        ),
        AT_IDOL to mapOf(
            ProcessionEventType.PROCESSION_STARTED to PROCESSION_STARTED,
        ),
        PROCESSION_STARTED to mapOf(
            ProcessionEventType.MOVING to MOVING,
        ),
        MOVING to mapOf(
            ProcessionEventType.REACHED_VISARJAN_AREA to REACHED_VISARJAN_AREA,
        ),
        REACHED_VISARJAN_AREA to mapOf(
            ProcessionEventType.VISARJAN_DONE to VISARJAN_DONE,
            ProcessionEventType.HOLDING to HOLDING,
        ),
        HOLDING to mapOf(
            ProcessionEventType.RETURNING_TO_PANDAL to RETURNING_TO_PANDAL,
        ),
        RETURNING_TO_PANDAL to mapOf(
            ProcessionEventType.RETURNED_TO_PANDAL to RETURNED_TO_PANDAL,
        ),
        RETURNED_TO_PANDAL to emptyMap(),
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

    /** True while GPS telemetry should keep being collected for this state, per spec section 42. */
    fun shouldContinueGpsTracking(state: ProcessionState): Boolean = when (state) {
        ASSIGNED, AT_IDOL -> false
        PROCESSION_STARTED, MOVING, REACHED_VISARJAN_AREA, HOLDING, RETURNING_TO_PANDAL -> true
        RETURNED_TO_PANDAL, VISARJAN_DONE -> false
    }

    /** Ordered list used to render the timeline UI, independent of which ones actually occurred. */
    val timelineOrder: List<ProcessionState> = listOf(
        PROCESSION_STARTED, MOVING, REACHED_VISARJAN_AREA, VISARJAN_DONE, HOLDING, RETURNING_TO_PANDAL, RETURNED_TO_PANDAL,
    )
}
