package com.ganeshvisarjan.fieldtracker.domain.usecase

import com.ganeshvisarjan.fieldtracker.domain.model.TrackingSession
import com.ganeshvisarjan.fieldtracker.domain.model.TrackingSessionStatus
import com.google.common.truth.Truth.assertThat
import org.junit.Test

/**
 * Foreground-service restart-after-kill scenarios from the integration-hardening
 * audit (2026-09-23). Scenario A (Activity destroyed, service continues) is a
 * structural guarantee — the service never reads from an Activity — and
 * Scenario B (process killed/recreated) exercises this exact code path: a
 * fresh process's `onStartCommand` receiving a null Intent IS scenario C.
 */
class ServiceRestartDecisionTest {

    private fun session(status: TrackingSessionStatus) = TrackingSession(
        localSessionId = "local-1",
        serverSessionId = "server-1",
        gpid = "HYD-CMRZ-CMNR-0234",
        assignmentId = "assignment-1",
        startedAt = 1000L,
        stoppedAt = null,
        status = status,
    )

    // Scenario C: tracking active -> service restarted with null intent -> resume.
    @Test
    fun `scenario C - an ACTIVE session in Room is resumed, never recreated`() {
        val action = ServiceRestartDecision.decide(session(TrackingSessionStatus.ACTIVE))

        assertThat(action).isEqualTo(ServiceRestartDecision.Action.Resume("local-1", "HYD-CMRZ-CMNR-0234"))
    }

    // Scenario D: no active tracking session -> service receives null intent -> must NOT begin tracking.
    @Test
    fun `scenario D - no session at all results in DoNothing`() {
        val action = ServiceRestartDecision.decide(null)

        assertThat(action).isEqualTo(ServiceRestartDecision.Action.DoNothing)
    }

    // Scenario E: tracking stopped -> service restarted -> must NOT restart GPS.
    @Test
    fun `scenario E - a STOPPED session results in DoNothing, not a resume`() {
        val action = ServiceRestartDecision.decide(session(TrackingSessionStatus.STOPPED))

        assertThat(action).isEqualTo(ServiceRestartDecision.Action.DoNothing)
    }

    @Test
    fun `a STOP_REQUESTED session (stop asked for but not yet finalized) does not resume GPS either`() {
        val action = ServiceRestartDecision.decide(session(TrackingSessionStatus.STOP_REQUESTED))

        assertThat(action).isEqualTo(ServiceRestartDecision.Action.DoNothing)
    }

    @Test
    fun `every non-ACTIVE status results in DoNothing`() {
        val nonActiveStatuses = TrackingSessionStatus.entries.filter { it != TrackingSessionStatus.ACTIVE }

        nonActiveStatuses.forEach { status ->
            val action = ServiceRestartDecision.decide(session(status))
            assertThat(action).isEqualTo(ServiceRestartDecision.Action.DoNothing)
        }
    }
}
