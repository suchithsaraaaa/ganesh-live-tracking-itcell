package com.ganeshvisarjan.fieldtracker.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/**
 * Request for the CONFIRMED `POST /api/v1/tracking/start/`
 * (`apps/tracking/views.py::StartTrackingView`, re-verified 2026-09-23 — see
 * docs/API_CONTRACT.md). This is the real, tested, server-side 50m + geocoding-
 * confidence start gate — there is no separate procession-start endpoint.
 *
 * [latitude]/[longitude] are the officer's fresh device GPS fix at the moment of
 * the request. The gate distance check ONLY runs server-side if these are
 * present — omitting them lets the request succeed on geocoding-confidence
 * alone, which is NOT the intended security boundary. Callers must always
 * supply a fresh fix here.
 */
@Serializable
data class StartTrackingRequestDto(
    @SerialName("assignment_id") val assignmentId: String,
    val gpid: String,
    val latitude: Double,
    val longitude: Double,
    @SerialName("device_info") val deviceInfo: String,
)

/**
 * Response from `POST /api/v1/tracking/start/` — mirrors `TrackingSessionSerializer`
 * exactly (`apps/tracking/serializers.py`). [id] is the server-generated session
 * id (a JSON integer; kept as [String] here and decoded via the shared lenient
 * Json config, the same pattern used for [IdolDto]'s decimal lat/lon).
 */
@Serializable
data class StartTrackingResponseDto(
    val id: String,
    val assignment: Int,
    val gpid: String,
    @SerialName("idol_name") val idolName: String? = null,
    @SerialName("police_station") val policeStation: String? = null,
    @SerialName("constable_name") val constableName: String? = null,
    @SerialName("constable_username") val constableUsername: String? = null,
    @SerialName("device_info") val deviceInfo: String? = null,
    @SerialName("started_at") val startedAt: String,
    @SerialName("ended_at") val endedAt: String? = null,
    val status: String,
    @SerialName("created_at") val createdAt: String? = null,
)

/**
 * Request for the CONFIRMED `POST /api/v1/tracking/stop/` (`StopTrackingView`).
 * The view reads raw `request.data` (no serializer) for `session_id` / `gpid` /
 * `final_state` — there is no `stopped_at` field on the backend at all.
 * [finalState] is real and optional (`AT_VISARJAN` / `IMMERSION_COMPLETED`), but
 * this app does not yet decide when to set it — see "Procession lifecycle" in
 * docs/API_CONTRACT.md for why that mapping isn't implemented automatically.
 */
@Serializable
data class StopTrackingRequestDto(
    @SerialName("session_id") val sessionId: String,
    @SerialName("final_state") val finalState: String? = null,
)

/** One GPS fix as sent to tracking/location/batch/. Field names re-verified against `BatchIngestLocationSerializer`. */
@Serializable
data class TelemetryPointDto(
    /**
     * Sent for forward-compatibility, but NOT relied upon: the confirmed
     * backend's `BatchIngestLocationView` does not read this field at all —
     * its dedup key is purely `(session_id, recorded_at)` server-side (see
     * docs/API_CONTRACT.md). True idempotency against a retried point that
     * gets a different `recorded_at` is not guaranteed server-side today.
     */
    @SerialName("client_event_id") val clientEventId: String,
    val latitude: Double,
    val longitude: Double,
    val accuracy: Float? = null,
    val altitude: Double? = null,
    val speed: Float? = null,
    /** Backend field is `heading`, not `bearing` — re-verified against IngestLocationSerializer/BatchIngestLocationView. */
    val heading: Float? = null,
    @SerialName("recorded_at") val recordedAt: String, // ISO-8601 UTC
)

@Serializable
data class TelemetryBatchRequestDto(
    @SerialName("session_id") val sessionId: String,
    val points: List<TelemetryPointDto>,
)

/**
 * Response from `POST /api/v1/tracking/location/batch/` — matches exactly what
 * `BatchIngestLocationView.post()` returns, re-verified directly against the
 * view body (it is a plain dict, not a serializer):
 * `{status, received, inserted, duplicates_skipped}`.
 */
@Serializable
data class TelemetryBatchResponseDto(
    val status: String = "",
    val received: Int = 0,
    val inserted: Int = 0,
    @SerialName("duplicates_skipped") val duplicatesSkipped: Int = 0,
)
