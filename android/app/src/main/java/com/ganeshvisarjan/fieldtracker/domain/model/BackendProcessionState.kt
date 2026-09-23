package com.ganeshvisarjan.fieldtracker.domain.model

/**
 * The backend's own authoritative procession state, `Idol.procession_state`
 * (`apps/idols/models.py::ProcessionState`, confirmed against the live Django
 * repository 2026-09-23 — see "Procession lifecycle" in docs/API_CONTRACT.md).
 *
 * This is a DIFFERENT, SIMPLER state space than this app's client-side
 * [ProcessionState] (9 values, fully officer-event-driven) and the two are
 * deliberately NOT mapped onto one another:
 * - `MOVING`/`HOLDING` here are auto-derived server-side from raw GPS speed on
 *   every telemetry point — not an officer-tapped event.
 * - There is no backend equivalent at all for this app's
 *   `REACHED_VISARJAN_AREA`, `RETURNING_TO_PANDAL`, or `RETURNED_TO_PANDAL`.
 * - `HOLDING` here (reachable any time during `MOVING`) means something
 *   different from this app's `ProcessionState.HOLDING` (reachable only after
 *   `REACHED_VISARJAN_AREA` — a deliberate pause at the immersion site).
 *
 * Currently informational only: parsed from the idol detail response onto
 * [Idol.backendProcessionState] for future use (e.g. debugging, or reconciling
 * against the client-side state once a real mapping is confirmed) — it does
 * not drive [com.ganeshvisarjan.fieldtracker.domain.usecase.ProcessionStateMachine]
 * or any UI gating decision today. Do not add such a mapping without first
 * confirming it against real backend behavior, per the audit that produced
 * this type.
 */
enum class BackendProcessionState {
    NOT_STARTED,
    TRACKING,
    MOVING,
    HOLDING,
    AT_VISARJAN,
    IMMERSION_COMPLETED,
    /** The backend returned no `procession_state`, or a value this app doesn't recognize yet. */
    UNKNOWN;

    companion object {
        fun fromRaw(raw: String?): BackendProcessionState = entries.find { it.name == raw } ?: UNKNOWN
    }
}
