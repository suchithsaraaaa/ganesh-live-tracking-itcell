package com.ganeshvisarjan.fieldtracker.domain.usecase

import com.ganeshvisarjan.fieldtracker.core.config.AppConfig
import com.ganeshvisarjan.fieldtracker.domain.model.AssignmentStatus
import com.ganeshvisarjan.fieldtracker.domain.model.GeoPoint
import javax.inject.Inject

/**
 * Client-side readiness check for the "Start Procession" action. This is UX
 * only: it lets the button show the right disabled reason immediately before
 * a network call is even attempted. It is NOT the security boundary — the
 * backend independently re-validates the request when it lands
 * (`POST /tracking/start/`, `StartTrackingView`) and its response is the only
 * thing that actually starts a session (see docs/API_CONTRACT.md).
 *
 * Product-decision change (2026-09-23): there is NO proximity/distance
 * requirement between the officer and the idol's registered origin anymore.
 * The registered origin (`Idol.originLocation`) is reference data only — never
 * an authorization gate — and this use case does not read it. The
 * authorization surface is now: an active assignment, and a fresh, valid,
 * sufficiently-accurate GPS fix. Everything else (whether the backend accepts
 * the request at all) is the backend's call, not this app's.
 */
class ValidateProcessionStartUseCase @Inject constructor() {

    sealed class Result {
        data class Ready(val accuracyMeters: Float) : Result()
        object WaitingForGps : Result()
        data class GpsAccuracyTooLow(val accuracyMeters: Float, val thresholdMeters: Float) : Result()
        object PreciseLocationRequired : Result()
        object AssignmentNotActive : Result()
        object AlreadyStarted : Result()
    }

    operator fun invoke(
        officerLocation: GeoPoint?,
        officerAccuracyMeters: Float?,
        hasPreciseLocationPermission: Boolean,
        assignmentStatus: AssignmentStatus,
        alreadyStarted: Boolean,
    ): Result {
        if (alreadyStarted) return Result.AlreadyStarted
        if (assignmentStatus != AssignmentStatus.ACTIVE) return Result.AssignmentNotActive
        if (!hasPreciseLocationPermission) return Result.PreciseLocationRequired
        if (officerLocation == null || officerAccuracyMeters == null) return Result.WaitingForGps

        if (officerAccuracyMeters > AppConfig.gpsAccuracyThresholdMeters) {
            return Result.GpsAccuracyTooLow(officerAccuracyMeters, AppConfig.gpsAccuracyThresholdMeters)
        }

        return Result.Ready(officerAccuracyMeters)
    }
}
