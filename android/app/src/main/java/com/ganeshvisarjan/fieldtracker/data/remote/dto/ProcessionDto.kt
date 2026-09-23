package com.ganeshvisarjan.fieldtracker.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/** CONCEPTUAL — no apps/processions app exists yet. See docs/API_CONTRACT.md. */
@Serializable
data class ProcessionStartRequestDto(
    @SerialName("assignment_id") val assignmentId: String,
    val gpid: String,
    val latitude: Double,
    val longitude: Double,
    @SerialName("accuracy") val accuracyMeters: Float? = null,
    @SerialName("occurred_at") val occurredAt: String,
)

@Serializable
data class ProcessionEventRequestDto(
    @SerialName("client_event_id") val clientEventId: String,
    @SerialName("assignment_id") val assignmentId: String,
    val gpid: String,
    @SerialName("event_type") val eventType: String,
    val latitude: Double,
    val longitude: Double,
    @SerialName("occurred_at") val occurredAt: String,
)

/** The backend's authoritative resulting state after a start/event request. */
@Serializable
data class ProcessionStateResponseDto(
    val gpid: String,
    val state: String,
    @SerialName("occurred_at") val occurredAt: String? = null,
)

/** 409-style business rejection, e.g. distance > 50m (spec section 8). */
@Serializable
data class ProcessionRejectionDto(
    val error: String,
    @SerialName("distance_meters") val distanceMeters: Double? = null,
    @SerialName("max_distance_meters") val maxDistanceMeters: Double? = null,
)
