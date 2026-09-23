package com.ganeshvisarjan.fieldtracker.domain.model

/**
 * Authoritative procession lifecycle state. The backend owns this value; the
 * Android UI mirrors whatever the server returns after each transition request.
 * This is intentionally ONE enum rather than a bag of booleans (isMoving,
 * isHolding, ...) so an invalid/contradictory combination cannot exist.
 */
enum class ProcessionState {
    ASSIGNED,
    AT_IDOL,
    PROCESSION_STARTED,
    MOVING,
    REACHED_VISARJAN_AREA,
    HOLDING,
    RETURNING_TO_PANDAL,
    RETURNED_TO_PANDAL,
    VISARJAN_DONE;

    companion object {
        fun fromRaw(raw: String?): ProcessionState? = entries.find { it.name == raw }
    }
}

/** The action a field officer can explicitly trigger from a given state. */
enum class ProcessionEventType {
    PROCESSION_STARTED,
    MOVING,
    REACHED_VISARJAN_AREA,
    VISARJAN_DONE,
    HOLDING,
    RETURNING_TO_PANDAL,
    RETURNED_TO_PANDAL;

    companion object {
        fun fromRaw(raw: String?): ProcessionEventType? = entries.find { it.name == raw }
    }
}
