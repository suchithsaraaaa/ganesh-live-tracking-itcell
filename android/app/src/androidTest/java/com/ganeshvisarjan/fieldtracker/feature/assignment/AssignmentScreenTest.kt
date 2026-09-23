package com.ganeshvisarjan.fieldtracker.feature.assignment

import android.Manifest
import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.assertDoesNotExist
import androidx.compose.ui.test.assertExists
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.hasSetTextAction
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onAllNodes
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.rule.GrantPermissionRule
import com.ganeshvisarjan.fieldtracker.core.network.ApiError
import com.ganeshvisarjan.fieldtracker.core.network.ApiResult
import com.ganeshvisarjan.fieldtracker.domain.model.Assignment
import com.ganeshvisarjan.fieldtracker.domain.model.AssignmentStatus
import com.ganeshvisarjan.fieldtracker.domain.model.GeoPoint
import com.ganeshvisarjan.fieldtracker.domain.model.HeightClass
import com.ganeshvisarjan.fieldtracker.domain.model.Idol
import com.ganeshvisarjan.fieldtracker.domain.model.TrackingSession
import com.ganeshvisarjan.fieldtracker.domain.model.TrackingSessionStatus
import com.ganeshvisarjan.fieldtracker.domain.repository.AssignmentRepository
import com.ganeshvisarjan.fieldtracker.domain.repository.ProcessionRepository
import com.ganeshvisarjan.fieldtracker.domain.repository.TrackingRepository
import com.ganeshvisarjan.fieldtracker.domain.usecase.ValidateProcessionStartUseCase
import com.ganeshvisarjan.fieldtracker.location.LocationClient
import com.ganeshvisarjan.fieldtracker.location.LocationFix
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.mockk
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Tests actual user-visible gating behavior (is the START PROCESSION button
 * enabled, and does it say why not) rather than just checking text presence.
 * [AssignmentViewModel] is constructed directly (bypassing `hiltViewModel()`)
 * with a real [ValidateProcessionStartUseCase] — the same pure gate logic the
 * app runs in production — and faked repositories/location client.
 *
 * Product-decision change (2026-09-23): the 50-meter proximity-to-idol-origin
 * requirement was removed from Start Procession entirely. There is
 * deliberately no test here asserting `distance <= 50m` for anything — see
 * `officerFarFromRegisteredOrigin_isStillAllowedToStart` for the explicit
 * proof the old rule is gone, and docs/API_CONTRACT.md / README.md for the
 * full write-up.
 */
@RunWith(AndroidJUnit4::class)
class AssignmentScreenTest {

    @get:Rule
    val composeRule = createComposeRule()

    // The gate needs ACCESS_FINE_LOCATION granted to reach the readiness
    // check at all (see AssignmentViewModel.refreshPermissionState).
    @get:Rule
    val permissionRule: GrantPermissionRule = GrantPermissionRule.grant(Manifest.permission.ACCESS_FINE_LOCATION)

    // The idol's registered origin — reference data only. None of these tests
    // compute or assert a distance from it; it exists purely so Idol/Assignment
    // are constructed realistically.
    private val registeredOrigin = GeoPoint(17.361200, 78.474900)

    private fun idol() = Idol(
        gpid = "HYD-CMRZ-CMNR-0234",
        ownerName = "Ramesh Reddy",
        associationName = "Charminar Youth Ganesh Mandal",
        heightFeet = 22.0,
        heightClass = HeightClass.fromHeightFeet(22.0),
        isOperationalEligible = true,
        originAddress = "Near Charminar, Pathergatti",
        originZone = "Zone 4",
        originLocation = registeredOrigin,
        startGateEligible = true,
        destinationAddress = "Hussain Sagar Visarjan Point",
        currentZone = "Zone 4",
        currentLocation = null,
        contactNumber = "9XXXXXXXXX",
    )

    private fun assignment() = Assignment(
        assignmentId = "assignment-1",
        officerId = 1001,
        idol = idol(),
        status = AssignmentStatus.ACTIVE,
        assignedAt = "2026-09-22T09:00:00Z",
    )

    private fun fixAt(point: GeoPoint, accuracyMeters: Float) = LocationFix(
        latitude = point.latitude,
        longitude = point.longitude,
        accuracyMeters = accuracyMeters,
        altitudeMeters = null,
        speedMetersPerSecond = null,
        bearingDegrees = null,
        timestampMillis = System.currentTimeMillis(),
    )

    /** Well within any distance anyone would call "near" the registered origin. */
    private fun nearbyPoint() = GeoPoint(registeredOrigin.latitude + 30.0 / 111_320.0, registeredOrigin.longitude)

    /** New Delhi — roughly 1,500km from Hyderabad. Deliberately absurdly far. */
    private fun veryFarAwayPoint() = GeoPoint(28.6139, 77.2090)

    private fun buildViewModel(
        assignmentResult: Assignment? = assignment(),
        fix: LocationFix? = fixAt(nearbyPoint(), 8f),
        startSessionResult: ApiResult<TrackingSession>? = null,
        trackingRepository: TrackingRepository? = null,
        processionRepository: ProcessionRepository? = null,
    ): AssignmentViewModel {
        val assignmentRepository: AssignmentRepository = mockk {
            coEvery { getActiveAssignment() } returns ApiResult.Success(assignmentResult)
        }
        val resolvedTrackingRepository: TrackingRepository = trackingRepository ?: mockk(relaxed = true) {
            if (startSessionResult != null) {
                coEvery { startSession(any(), any(), any(), any(), any()) } returns startSessionResult
            }
        }
        val resolvedProcessionRepository: ProcessionRepository = processionRepository ?: mockk(relaxed = true)
        val locationClient: LocationClient = mockk {
            coEvery { getCurrentLocation() } returns fix
        }
        return AssignmentViewModel(
            context = ApplicationProvider.getApplicationContext(),
            assignmentRepository = assignmentRepository,
            trackingRepository = resolvedTrackingRepository,
            processionRepository = resolvedProcessionRepository,
            locationClient = locationClient,
            validateStart = ValidateProcessionStartUseCase(),
        )
    }

    @Test
    fun activeAssignment_isDisplayed() {
        composeRule.setContent {
            AssignmentScreen(onProcessionStarted = {}, viewModel = buildViewModel())
        }

        composeRule.onNodeWithText("HYD-CMRZ-CMNR-0234").assertExists()
    }

    @Test
    fun noActiveAssignment_doesNotShowTheStartFlow() {
        composeRule.setContent {
            AssignmentScreen(onProcessionStarted = {}, viewModel = buildViewModel(assignmentResult = null, fix = null))
        }

        composeRule.onNodeWithText("CHECK LOCATION").assertDoesNotExist()
        composeRule.onNodeWithText("START PROCESSION").assertDoesNotExist()
    }

    // Test A (explicit proof the old 50m rule is gone): a GPS fix roughly
    // 1,500km from the idol's registered origin must NOT be rejected — there
    // is no distance parameter left anywhere in this call path to reject it with.
    @Test
    fun officerFarFromRegisteredOrigin_isStillAllowedToStart() {
        composeRule.setContent {
            AssignmentScreen(onProcessionStarted = {}, viewModel = buildViewModel(fix = fixAt(veryFarAwayPoint(), 8f)))
        }

        composeRule.onNodeWithText("CHECK LOCATION").performClick()
        composeRule.waitForIdle()

        composeRule.onNodeWithText("START PROCESSION").assertIsEnabled()
        composeRule.onNodeWithText("Ready to start — ±8m accuracy.").assertExists()
    }

    // Test B: no GPS fix at all -> rejected locally, Start stays disabled.
    @Test
    fun startDisabled_whenNoGpsFixIsAvailable() {
        composeRule.setContent {
            AssignmentScreen(onProcessionStarted = {}, viewModel = buildViewModel(fix = null))
        }

        composeRule.onNodeWithText("CHECK LOCATION").performClick()
        composeRule.waitForIdle()

        composeRule.onNodeWithText("START PROCESSION").assertIsNotEnabled()
        composeRule.onNodeWithText("Getting your current location…").assertExists()
    }

    // Test C: a fix with an out-of-range (invalid) coordinate -> rejected
    // locally the same way as no fix at all (GeoPoint.ofOrNull filters it).
    @Test
    fun startDisabled_whenGpsFixHasAnInvalidCoordinate() {
        val invalidFix = LocationFix(
            latitude = 999.0, // out of range — GeoPoint.ofOrNull rejects this
            longitude = 78.47,
            accuracyMeters = 8f,
            altitudeMeters = null,
            speedMetersPerSecond = null,
            bearingDegrees = null,
            timestampMillis = System.currentTimeMillis(),
        )
        composeRule.setContent {
            AssignmentScreen(onProcessionStarted = {}, viewModel = buildViewModel(fix = invalidFix))
        }

        composeRule.onNodeWithText("CHECK LOCATION").performClick()
        composeRule.waitForIdle()

        composeRule.onNodeWithText("START PROCESSION").assertIsNotEnabled()
        composeRule.onNodeWithText("Getting your current location…").assertExists()
    }

    @Test
    fun startDisabled_whenGpsAccuracyIsPoor() {
        composeRule.setContent {
            AssignmentScreen(onProcessionStarted = {}, viewModel = buildViewModel(fix = fixAt(nearbyPoint(), 95f)))
        }

        composeRule.onNodeWithText("CHECK LOCATION").performClick()
        composeRule.waitForIdle()

        composeRule.onNodeWithText("START PROCESSION").assertIsNotEnabled()
        composeRule.onNodeWithText("Unable to obtain a precise enough location (±95m). Move to open sky and try again.").assertExists()
    }

    // Test D: valid GPS + backend acceptance -> accepted, local event recorded,
    // and the screen navigates on (which is what starts foreground tracking,
    // via TrackingScreen's own LaunchedEffect — see LocationTrackingService).
    @Test
    fun validGpsAndBackendSuccess_startsTheProcessionAndNavigatesOn() {
        val session = TrackingSession(
            localSessionId = "local-1", serverSessionId = "server-1", gpid = "HYD-CMRZ-CMNR-0234",
            assignmentId = "assignment-1", startedAt = 1_000L, stoppedAt = null,
            status = TrackingSessionStatus.ACTIVE, startLocation = nearbyPoint(),
        )
        val processionRepository: ProcessionRepository = mockk(relaxed = true)
        var navigatedSessionId: String? = null

        composeRule.setContent {
            AssignmentScreen(
                onProcessionStarted = { navigatedSessionId = it },
                viewModel = buildViewModel(
                    startSessionResult = ApiResult.Success(session),
                    processionRepository = processionRepository,
                ),
            )
        }

        composeRule.onNodeWithText("CHECK LOCATION").performClick()
        composeRule.waitForIdle()
        composeRule.onNodeWithText("START PROCESSION").performClick()
        composeRule.waitForIdle()

        assert(navigatedSessionId == "local-1") { "Expected navigation to fire with the new session's local id, got $navigatedSessionId" }
        coVerify(exactly = 1) { processionRepository.recordLocalStart(any(), any(), any(), any()) }
    }

    // Test E: valid GPS + backend rejection -> NOT considered active, backend
    // error shown, and no navigation (so foreground tracking never begins).
    @Test
    fun validGpsAndBackendRejection_doesNotStartAnythingAndShowsTheBackendError() {
        val processionRepository: ProcessionRepository = mockk(relaxed = true)
        var navigatedSessionId: String? = null

        composeRule.setContent {
            AssignmentScreen(
                onProcessionStarted = { navigatedSessionId = it },
                viewModel = buildViewModel(
                    startSessionResult = ApiResult.Error(ApiError.BadRequest("Some backend business-rule rejection.")),
                    processionRepository = processionRepository,
                ),
            )
        }

        composeRule.onNodeWithText("CHECK LOCATION").performClick()
        composeRule.waitForIdle()
        composeRule.onNodeWithText("START PROCESSION").performClick()
        composeRule.waitForIdle()

        composeRule.onNodeWithText("Some backend business-rule rejection.").assertExists()
        assert(navigatedSessionId == null) { "Must not navigate into tracking when the backend rejected the start request." }
        coVerify(exactly = 0) { processionRepository.recordLocalStart(any(), any(), any(), any()) }
    }

    // Test F: the officer is restricted to the backend-provided assignment —
    // no GPID picker, no free-text GPID entry anywhere on this screen.
    @Test
    fun noGpidPickerOrFreeTextInputExistsAnywhereOnTheScreen() {
        composeRule.setContent {
            AssignmentScreen(onProcessionStarted = {}, viewModel = buildViewModel())
        }

        composeRule.onAllNodes(hasSetTextAction()).assertCountEquals(0)
    }
}
