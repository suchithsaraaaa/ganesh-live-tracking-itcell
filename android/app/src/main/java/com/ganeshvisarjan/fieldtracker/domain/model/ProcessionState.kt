package com.ganeshvisarjan.fieldtracker.domain.model

/**
 * Authoritative procession lifecycle state. The backend owns this value; the
 * Android UI mirrors whatever the server returns after each transition request.
 * This is intentionally ONE enum rather than a bag of booleans (isMoving,
 * isHolding, ...) so an invalid/contradictory combination cannot exist.
 */
enum class ProcessionState {
    ASSIGNED,
    REACHED_SITE,
    PROCESSION_STARTED,
    REACHED_VISARJAN_SITE,
    VISARJAN_DONE,
    VISARJAN_NOT_DONE,
    SENT_TO_HOLDING,
    RETURNED_TO_ORIGIN;

    companion object {
        fun fromRaw(raw: String?): ProcessionState? = when (raw) {
            "AT_IDOL" -> REACHED_SITE
            "MOVING" -> PROCESSION_STARTED
            "REACHED_VISARJAN_AREA" -> REACHED_VISARJAN_SITE
            "HOLDING" -> SENT_TO_HOLDING
            "RETURNING_TO_PANDAL" -> SENT_TO_HOLDING
            "RETURNED_TO_PANDAL" -> RETURNED_TO_ORIGIN
            else -> entries.find { it.name.equals(raw, ignoreCase = true) }
        }
    }
}

/** The action a field officer can explicitly trigger from a given state. */
enum class ProcessionEventType {
    REACHED_SITE,
    PROCESSION_STARTED,
    REACHED_VISARJAN_SITE,
    VISARJAN_DONE,
    VISARJAN_NOT_DONE,
    SENT_TO_HOLDING,
    RETURNED_TO_ORIGIN;

    companion object {
        fun fromRaw(raw: String?): ProcessionEventType? = when (raw) {
            "AT_IDOL" -> REACHED_SITE
            "MOVING" -> REACHED_VISARJAN_SITE
            "REACHED_VISARJAN_AREA" -> REACHED_VISARJAN_SITE
            "HOLDING" -> SENT_TO_HOLDING
            "RETURNING_TO_PANDAL" -> SENT_TO_HOLDING
            "RETURNED_TO_PANDAL" -> RETURNED_TO_ORIGIN
            else -> entries.find { it.name.equals(raw, ignoreCase = true) }
        }
    }
}
