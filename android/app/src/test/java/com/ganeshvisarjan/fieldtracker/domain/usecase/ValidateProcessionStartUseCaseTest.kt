package com.ganeshvisarjan.fieldtracker.domain.usecase

import com.ganeshvisarjan.fieldtracker.domain.model.AssignmentStatus
import com.ganeshvisarjan.fieldtracker.domain.model.GeoPoint
import com.google.common.truth.Truth.assertThat
import org.junit.Test

/**
 * Product-decision change (2026-09-23): the 50-meter proximity-to-idol-origin
 * requirement was removed from the Start Procession flow entirely — see
 * docs/API_CONTRACT.md and README.md "Known limitations". This use case no
 * longer accepts an idol origin coordinate at all, so there is no way to
 * express (or accidentally reintroduce) a distance check here — that's
 * deliberate, not an oversight. What remains is purely: active assignment +
 * a fresh, sufficiently-accurate GPS fix. Whatever the backend itself
 * currently enforces on `POST /tracking/start/` is validated there, not here
 * — see [TrackingRepositoryImplSyncTest] for proof the network layer sends a
 * GPS fix with zero client-side distance computation regardless of where it is.
 */
class ValidateProcessionStartUseCaseTest {

    private val useCase = ValidateProcessionStartUseCase()
    private val somewhereInHyderabad = GeoPoint(17.385044, 78.486671)
    private val goodAccuracy = 10f

    private fun invoke(
        location: GeoPoint? = somewhereInHyderabad,
        accuracy: Float? = goodAccuracy,
        hasPrecise: Boolean = true,
        status: AssignmentStatus = AssignmentStatus.ACTIVE,
        alreadyStarted: Boolean = false,
    ) = useCase(
        officerLocation = location,
        officerAccuracyMeters = accuracy,
        hasPreciseLocationPermission = hasPrecise,
        assignmentStatus = status,
        alreadyStarted = alreadyStarted,
    )

    @Test
    fun `a valid fresh GPS fix with good accuracy and an active assignment is ready, with no distance requirement`() {
        assertThat(invoke()).isInstanceOf(ValidateProcessionStartUseCase.Result.Ready::class.java)
    }

    @Test
    fun `a location far from anything idol-related is still ready — there is no origin parameter to even supply`() {
        // New Delhi — nowhere near any Hyderabad idol. The use case has no
        // parameter that would let it reject this for distance, by design.
        val farAwayLocation = GeoPoint(28.6139, 77.2090)
        val result = invoke(location = farAwayLocation)
        assertThat(result).isInstanceOf(ValidateProcessionStartUseCase.Result.Ready::class.java)
    }

    @Test
    fun `gps unavailable is rejected`() {
        assertThat(invoke(location = null, accuracy = null))
            .isInstanceOf(ValidateProcessionStartUseCase.Result.WaitingForGps::class.java)
    }

    @Test
    fun `a fix with no accuracy reading is treated as not ready yet`() {
        assertThat(invoke(accuracy = null)).isInstanceOf(ValidateProcessionStartUseCase.Result.WaitingForGps::class.java)
    }

    @Test
    fun `poor gps accuracy is rejected even though the location itself is fine`() {
        assertThat(invoke(accuracy = 95f))
            .isInstanceOf(ValidateProcessionStartUseCase.Result.GpsAccuracyTooLow::class.java)
    }

    @Test
    fun `no active assignment is rejected`() {
        assertThat(invoke(status = AssignmentStatus.COMPLETED))
            .isInstanceOf(ValidateProcessionStartUseCase.Result.AssignmentNotActive::class.java)
    }

    @Test
    fun `already started is rejected`() {
        assertThat(invoke(alreadyStarted = true)).isInstanceOf(ValidateProcessionStartUseCase.Result.AlreadyStarted::class.java)
    }

    @Test
    fun `missing precise location permission is rejected`() {
        assertThat(invoke(hasPrecise = false)).isInstanceOf(ValidateProcessionStartUseCase.Result.PreciseLocationRequired::class.java)
    }
}
