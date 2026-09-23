package com.ganeshvisarjan.fieldtracker.domain.model

/**
 * Mirrors the backend's real 4-tier role field (apps/accounts/models.py UserRole).
 * The backend remains authoritative for what a role may do — this enum exists so
 * the UI can react to a known role, not to independently decide permissions.
 */
enum class Role {
    MAIN_OFFICER,
    ACP,
    SHO,
    CONSTABLE,
    UNKNOWN;

    companion object {
        fun fromRaw(raw: String?): Role = entries.find { it.name == raw } ?: UNKNOWN
    }
}

data class User(
    val id: Int,
    val username: String,
    val displayName: String,
    val role: Role,
    val policeStation: String?,
    val zone: String?,
    val division: String?,
)
