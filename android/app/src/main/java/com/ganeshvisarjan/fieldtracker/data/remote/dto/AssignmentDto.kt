package com.ganeshvisarjan.fieldtracker.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/** Mirrors AssignmentSerializer fields in apps/assignments/serializers.py. */
@Serializable
data class AssignmentDto(
    val id: Int,
    val idol: Int,
    @SerialName("idol_gpid") val idolGpid: String,
    @SerialName("idol_name") val idolName: String? = null,
    @SerialName("police_station") val policeStation: String? = null,
    val constable: Int,
    @SerialName("is_active") val isActive: Boolean,
    @SerialName("started_at") val startedAt: String,
)

@Serializable
data class AssignmentListResponseDto(
    val count: Int,
    val next: String? = null,
    val previous: String? = null,
    val results: List<AssignmentDto> = emptyList(),
)

/**
 * Response from the CONFIRMED `GET /api/v1/assignments/current/`
 * (`CurrentAssignmentView`, re-verified 2026-09-23) — the real "my active
 * assignment" endpoint, scoped server-side to the caller. Replaces the old
 * "page 1 of the list, pick is_active" workaround.
 */
@Serializable
data class CurrentAssignmentResponseDto(
    @SerialName("active_assignment") val activeAssignment: CurrentAssignmentDto? = null,
)

/**
 * A flat, denormalized shape — deliberately NOT the same as [AssignmentDto].
 * No `constable`/officer id is returned (the endpoint is inherently "my own",
 * so the backend doesn't repeat it) — [com.ganeshvisarjan.fieldtracker.domain.model.Assignment.officerId]
 * is left null when mapped from this response rather than fabricated.
 */
@Serializable
data class CurrentAssignmentDto(
    @SerialName("assignment_id") val assignmentId: Int,
    val gpid: String,
    @SerialName("idol_id") val idolId: Int,
    val name: String? = null,
    @SerialName("association_name") val associationName: String? = null,
    @SerialName("police_station") val policeStation: String? = null,
    val zone: String? = null,
    @SerialName("procession_state") val processionState: String? = null,
    @SerialName("started_at") val startedAt: String,
)

/**
 * Mirrors IdolDetailSerializer in apps/idols/serializers.py — confirmed against
 * the backend directly (it was extended with real geocoding fields partway
 * through building this app; see docs/API_CONTRACT.md for the before/after).
 *
 * [latitude]/[longitude] are Django DecimalFields, which DRF renders as JSON
 * *strings* by default (not bare numbers) to preserve precision — relies on
 * the shared `Json { isLenient = true }` config (di/NetworkModule.kt) to parse
 * a quoted decimal into a Kotlin Double.
 *
 * [startGateEligible] is the backend's own answer to "is this coordinate
 * trustworthy enough to gate a real-world action on" (geocoding_confidence is
 * EXACT/HIGH AND both coordinates are present). Parsed and kept for reference,
 * but as of the 2026-09-23 product decision it no longer gates anything
 * client-side — `ValidateProcessionStartUseCase` doesn't read [latitude]/
 * [longitude]/[startGateEligible] at all anymore; see docs/API_CONTRACT.md.
 */
@Serializable
data class IdolDto(
    val gpid: String,
    val name: String? = null,
    @SerialName("association_name") val associationName: String? = null,
    @SerialName("idol_height") val idolHeightFeet: Double? = null,
    val address: String? = null,
    val zone: String? = null,
    @SerialName("police_station") val policeStation: String? = null,
    @SerialName("river_name") val riverName: String? = null,
    val latitude: Double? = null,
    val longitude: Double? = null,
    @SerialName("geocoding_confidence") val geocodingConfidence: String? = null,
    @SerialName("start_gate_eligible") val startGateEligible: Boolean = false,
    @SerialName("height_classification") val heightClassification: String? = null,
    @SerialName("is_operational_eligible") val isOperationalEligible: Boolean = false,
    /**
     * The backend's OWN authoritative procession state (`Idol.procession_state`,
     * confirmed 2026-09-23 — see [com.ganeshvisarjan.fieldtracker.domain.model.BackendProcessionState]
     * for why this is intentionally NOT mapped onto this app's client-side
     * [com.ganeshvisarjan.fieldtracker.domain.model.ProcessionState]).
     */
    @SerialName("procession_state") val processionState: String? = null,
    @SerialName("contact_info") val contactInfo: ContactInfoDto? = null,
)

@Serializable
data class ContactInfoDto(
    @SerialName("mobile_no") val mobileNo: String? = null,
)
