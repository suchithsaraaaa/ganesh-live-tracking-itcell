package com.ganeshvisarjan.fieldtracker.feature.assignment

import android.content.Context
import android.os.Build
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ganeshvisarjan.fieldtracker.core.network.ApiResult
import com.ganeshvisarjan.fieldtracker.domain.model.Assignment
import com.ganeshvisarjan.fieldtracker.domain.model.GeoPoint
import com.ganeshvisarjan.fieldtracker.domain.repository.AssignmentRepository
import com.ganeshvisarjan.fieldtracker.domain.repository.ProcessionRepository
import com.ganeshvisarjan.fieldtracker.domain.repository.TrackingRepository
import com.ganeshvisarjan.fieldtracker.domain.usecase.ValidateProcessionStartUseCase
import com.ganeshvisarjan.fieldtracker.location.LocationClient
import com.ganeshvisarjan.fieldtracker.location.LocationPermissions
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class AssignmentUiState(
    val assignment: Assignment? = null,
    val isLoading: Boolean = false,
    val isCheckingLocation: Boolean = false,
    val readiness: ValidateProcessionStartUseCase.Result? = null,
    val isStarting: Boolean = false,
    val startError: String? = null,
    val startedSessionLocalId: String? = null,
    val hasPreciseLocationPermission: Boolean = false,
)

@HiltViewModel
class AssignmentViewModel @Inject constructor(
    @ApplicationContext private val context: Context,
    private val assignmentRepository: AssignmentRepository,
    private val trackingRepository: TrackingRepository,
    private val processionRepository: ProcessionRepository,
    private val locationClient: LocationClient,
    private val validateStart: ValidateProcessionStartUseCase,
) : ViewModel() {

    private val _uiState = MutableStateFlow(AssignmentUiState())
    val uiState: StateFlow<AssignmentUiState> = _uiState.asStateFlow()

    init {
        refreshPermissionState()
        loadAssignment()
    }

    fun refreshPermissionState() {
        _uiState.value = _uiState.value.copy(hasPreciseLocationPermission = LocationPermissions.hasPreciseLocation(context))
    }

    fun loadAssignment() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true)
            when (val result = assignmentRepository.getActiveAssignment()) {
                is ApiResult.Success -> _uiState.value = _uiState.value.copy(isLoading = false, assignment = result.data)
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(isLoading = false)
            }
        }
    }

    /** "Check Location" — spec section 11: a fresh fix on demand, not continuous tracking yet. */
    fun checkLocation() {
        val assignment = _uiState.value.assignment ?: return
        refreshPermissionState()
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isCheckingLocation = true)
            val fix = locationClient.getCurrentLocation()
            val officerLocation = fix?.let { GeoPoint.ofOrNull(it.latitude, it.longitude) }
            val readiness = validateStart(
                officerLocation = officerLocation,
                officerAccuracyMeters = fix?.accuracyMeters,
                hasPreciseLocationPermission = _uiState.value.hasPreciseLocationPermission,
                assignmentStatus = assignment.status,
                alreadyStarted = _uiState.value.startedSessionLocalId != null,
            )
            _uiState.value = _uiState.value.copy(isCheckingLocation = false, readiness = readiness)
        }
    }

    /**
     * The client-side [ValidateProcessionStartUseCase] check ([readiness] being
     * [ValidateProcessionStartUseCase.Result.Ready]) only verifies an active
     * assignment and a fresh, sufficiently-accurate GPS fix — per the
     * 2026-09-23 product decision, this app no longer requires (or checks) any
     * proximity between the officer and the idol's registered origin.
     *
     * The confirmed, real authority for "start procession" is
     * `POST /tracking/start/` (`TrackingRepository.startSession` —
     * `apps/tracking/views.py::StartTrackingView`, see docs/API_CONTRACT.md).
     * This app does not predict or replicate whatever business rule the
     * backend currently enforces there — it submits the fresh GPS fix and
     * reacts to the response. A backend rejection is surfaced to the officer
     * as [AssignmentUiState.startError] with the backend's own business-rule
     * message (never silently treated as success); nothing is started locally
     * — no session, no local event, no foreground tracking — until the backend
     * accepts.
     */
    fun startProcession() {
        val assignment = _uiState.value.assignment ?: return
        val readiness = _uiState.value.readiness as? ValidateProcessionStartUseCase.Result.Ready ?: return

        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isStarting = true, startError = null)

            val fix = locationClient.getCurrentLocation()
            val location = fix?.let { GeoPoint.ofOrNull(it.latitude, it.longitude) }
            if (location == null) {
                _uiState.value = _uiState.value.copy(isStarting = false, startError = "Lost GPS fix — try again.")
                return@launch
            }

            val sessionResult = trackingRepository.startSession(
                assignmentId = assignment.assignmentId,
                gpid = assignment.idol.gpid,
                officerLocation = location,
                officerAccuracyMeters = fix.accuracyMeters,
                deviceInfo = "${Build.MANUFACTURER} ${Build.MODEL}",
            )
            when (sessionResult) {
                is ApiResult.Success -> {
                    // The real gate already confirmed this server-side — record it
                    // locally (no extra network call) so this app's own 9-state
                    // timeline UI advances past PROCESSION_STARTED.
                    processionRepository.recordLocalStart(
                        gpid = assignment.idol.gpid,
                        assignmentId = assignment.assignmentId,
                        trackingSessionLocalId = sessionResult.data.localSessionId,
                        location = location,
                    )
                    _uiState.value = _uiState.value.copy(
                        isStarting = false,
                        startedSessionLocalId = sessionResult.data.localSessionId,
                    )
                }
                is ApiResult.Error -> {
                    // Surface the backend's actual rejection message, whatever it is —
                    // never converted into success, never re-worded to guess a reason.
                    _uiState.value = _uiState.value.copy(isStarting = false, startError = sessionResult.error.message)
                }
            }
        }
    }
}
