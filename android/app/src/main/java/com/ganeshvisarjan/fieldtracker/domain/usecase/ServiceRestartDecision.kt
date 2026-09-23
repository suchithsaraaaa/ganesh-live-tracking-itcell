package com.ganeshvisarjan.fieldtracker.domain.usecase

import com.ganeshvisarjan.fieldtracker.domain.model.TrackingSession
import com.ganeshvisarjan.fieldtracker.domain.model.TrackingSessionStatus

/**
 * Pure decision logic for [com.ganeshvisarjan.fieldtracker.service.LocationTrackingService]'s
 * null-[android.content.Intent] case — the system can restart a killed
 * foreground service with `START_STICKY`, but the restart delivers no Intent,
 * so the original `ACTION_START` extras (session id, gpid) are gone. Extracted
 * into its own pure, DI-free object — same pattern as [ProcessionStateMachine]
 * and [ValidateProcessionStartUseCase] — so it's unit-testable without an
 * emulator or Hilt test infrastructure. Room's `observeActiveSession()` result
 * is the ONLY input this decision is based on; there is no other source of truth
 * (never a static var, never [com.ganeshvisarjan.fieldtracker.service.TrackingServiceState],
 * which is an in-memory UI mirror that is reset on every process start and is
 * therefore useless for recovering after the exact kind of process death this
 * exists to handle).
 */
object ServiceRestartDecision {

    sealed class Action {
        /** An ACTIVE session exists in Room — resume GPS collection for it. Never create a new session. */
        data class Resume(val sessionLocalId: String, val gpid: String) : Action()

        /** No active session, or the officer already requested a stop — do not (re)start GPS collection. */
        object DoNothing : Action()
    }

    fun decide(activeSession: TrackingSession?): Action {
        if (activeSession == null || activeSession.status != TrackingSessionStatus.ACTIVE) {
            return Action.DoNothing
        }
        return Action.Resume(activeSession.localSessionId, activeSession.gpid)
    }
}
