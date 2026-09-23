package com.ganeshvisarjan.fieldtracker.domain.model

enum class AssignmentStatus { ACTIVE, COMPLETED, CANCELLED, UNKNOWN;
    companion object {
        fun fromRaw(raw: String?): AssignmentStatus = entries.find { it.name == raw } ?: UNKNOWN
    }
}

/**
 * Which officer is responsible for which GPID. This is a DIFFERENT concept from
 * [com.ganeshvisarjan.fieldtracker.domain.model.ProcessionState] (what stage the
 * procession is in) and from GPS telemetry (where the device physically is) — see
 * section 41 of the spec this was built from. Do not collapse these.
 *
 * The officer never picks their own GPID; this is always fetched from the
 * backend's confirmed "my active assignment" endpoint, `GET /assignments/current/`.
 */
data class Assignment(
    val assignmentId: String,
    /**
     * Null when sourced from `GET /assignments/current/` — that response is
     * inherently scoped to "the caller's own assignment" and does not repeat
     * the officer's id (re-confirmed against `CurrentAssignmentView`). Left
     * null rather than fabricated; nothing in this app currently reads it.
     */
    val officerId: Int?,
    val idol: Idol,
    val status: AssignmentStatus,
    val assignedAt: String, // ISO-8601, kept as the raw wire format at this layer
)
