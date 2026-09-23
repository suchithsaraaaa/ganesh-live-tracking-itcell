package com.ganeshvisarjan.fieldtracker.domain.model

/**
 * Operationally relevant idol details for a field officer.
 *
 * IMPORTANT: [originLocation] and [currentLocation] are deliberately separate
 * fields and must never overwrite one another. [originLocation] is the idol's
 * fixed, registered coordinate — **reference/display data only**; current
 * location comes from the latest telemetry once tracking is underway. Same
 * for [originZone] vs [currentZone].
 *
 * Product-decision change (2026-09-23): [originLocation] is no longer an
 * authorization gate for anything. Earlier, [originLocation] and
 * [startGateEligible] fed a client-side 50-meter proximity check in
 * `ValidateProcessionStartUseCase` before an officer could start a procession
 * — that check has been removed entirely (see docs/API_CONTRACT.md,
 * README.md). [startGateEligible] is still parsed from the backend (its own
 * "is this coordinate trustworthy" signal — confidence EXACT/HIGH and both
 * coordinates present) but is now purely informational on the Android side;
 * nothing reads it to enable or disable Start Procession anymore.
 */
data class Idol(
    val gpid: String,
    val ownerName: String,
    val associationName: String?,
    val heightFeet: Double?,
    val heightClass: HeightClass,
    val isOperationalEligible: Boolean,
    val originAddress: String?,
    val originZone: String?,
    val originLocation: GeoPoint?,
    val startGateEligible: Boolean,
    val destinationAddress: String?,
    val currentZone: String?,
    val currentLocation: GeoPoint?,
    val contactNumber: String?,
    /** See [BackendProcessionState] for why this is not equated with the client-side procession state machine. */
    val backendProcessionState: BackendProcessionState = BackendProcessionState.UNKNOWN,
)
