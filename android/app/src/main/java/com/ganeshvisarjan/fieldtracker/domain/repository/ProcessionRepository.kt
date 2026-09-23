package com.ganeshvisarjan.fieldtracker.domain.repository

import com.ganeshvisarjan.fieldtracker.core.network.ApiResult
import com.ganeshvisarjan.fieldtracker.domain.model.GeoPoint
import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionEventRecord
import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionEventType
import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionState
import kotlinx.coroutines.flow.Flow

/**
 * Records procession lifecycle events. [ProcessionStateMachine] decides whether
 * an event is legal client-side; the backend independently re-validates and
 * returns the authoritative resulting [ProcessionState]. As of the 2026-09-23
 * product decision, starting a procession has no client-side proximity
 * requirement — see [recordLocalStart] and docs/API_CONTRACT.md.
 */
interface ProcessionRepository {

    fun observeState(gpid: String): Flow<ProcessionState?>
    fun observeTimeline(gpid: String): Flow<List<ProcessionEventRecord>>
    fun observePendingEventCount(): Flow<Int>

    /**
     * CONCEPTUAL / UNUSED BY THE REAL START FLOW. This talks to the fictional
     * `POST /processions/start/` (no `apps/processions` Django app exists — see
     * docs/API_CONTRACT.md). The confirmed, real start action is
     * `POST /tracking/start/` (`TrackingRepository.startSession`) — no
     * proximity check of any kind, client- or server-facing, is implied by
     * calling it. Once that succeeds, callers should record the local event
     * via [recordLocalStart] instead of calling this. Preserved as conceptual
     * scaffolding only, in case a dedicated procession-start endpoint is ever
     * built for real.
     */
    suspend fun submitProcessionStart(
        gpid: String,
        assignmentId: String,
        location: GeoPoint,
        accuracyMeters: Float?,
    ): ApiResult<ProcessionState>

    /**
     * Records the PROCESSION_STARTED event locally, already SYNCED — no
     * network call. Call this ONLY after the real backend gate
     * (`TrackingRepository.startSession`, `POST /tracking/start/`) has already
     * succeeded: that request IS the authoritative confirmation for this
     * transition, and there is no separate procession-start endpoint to
     * confirm it against (see docs/API_CONTRACT.md). This keeps the
     * client-side [ProcessionState] timeline (this app's 9-state machine)
     * advancing without inventing a network round trip the backend doesn't have.
     */
    suspend fun recordLocalStart(
        gpid: String,
        assignmentId: String,
        trackingSessionLocalId: String?,
        location: GeoPoint,
    )

    /**
     * Submits an event. If offline, persists it locally as PENDING (spec section
     * 23) and returns a Success carrying the OPTIMISTIC next state from
     * [com.ganeshvisarjan.fieldtracker.domain.usecase.ProcessionStateMachine] —
     * callers must treat that as provisional until sync confirms it.
     */
    suspend fun submitEvent(
        gpid: String,
        assignmentId: String,
        trackingSessionLocalId: String?,
        eventType: ProcessionEventType,
        location: GeoPoint,
    ): ApiResult<ProcessionState>

    /** Invoked by the sync worker; uploads pending events in chronological order (spec section 24). */
    suspend fun syncPendingEvents(): ApiResult<Int>
}
