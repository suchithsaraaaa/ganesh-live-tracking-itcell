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
import com.ganeshvisarjan.fieldtracker.location.LocationSetupStatus
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import timber.log.Timber
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
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
    val setupStatus: LocationSetupStatus = LocationSetupStatus(
        hasFineLocation = false,
        hasCoarseLocation = false,
        isLocationServiceEnabled = false,
        hasNotificationPermission = false,
        isBatteryOptimizationIgnored = false,
    ),
    val isRecordingReachedSite: Boolean = false,
    val reachedSiteRecorded: Boolean = false,
    val reachedSiteTimestamp: String? = null,
    val reachedSiteCoordinates: String? = null,
    val reachedSiteError: String? = null,
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

    private val prefs = context.getSharedPreferences("field_tracker_assignment_state", Context.MODE_PRIVATE)

    private val _uiState = MutableStateFlow(AssignmentUiState())
    val uiState: StateFlow<AssignmentUiState> = _uiState.asStateFlow()

    init {
        refreshPermissionState()
        loadAssignment()
    }

    fun refreshPermissionState(isPermanentlyDenied: Boolean = false) {
        val status = LocationPermissions.checkSetupStatus(context, isPermanentlyDenied)
        _uiState.value = _uiState.value.copy(
            setupStatus = status,
            hasPreciseLocationPermission = status.hasFineLocation,
        )
    }

    fun loadAssignment() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true)
            when (val result = assignmentRepository.getActiveAssignment()) {
                is ApiResult.Success -> {
                    val assignment = result.data
                    val gpid = assignment?.idol?.gpid
                    val isRecorded = if (gpid != null) prefs.getBoolean("reached_site_recorded_$gpid", false) else false
                    val timestamp = if (gpid != null) prefs.getString("reached_site_timestamp_$gpid", null) else null
                    val coords = if (gpid != null) prefs.getString("reached_site_coords_$gpid", null) else null

                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        assignment = assignment,
                        reachedSiteRecorded = isRecorded,
                        reachedSiteTimestamp = timestamp,
                        reachedSiteCoordinates = coords,
                    )
                }
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(isLoading = false)
            }
        }
    }

    /**
     * Records site arrival by the assigned officer.
     * Guaranteed never to crash: checks runtime permissions before querying location,
     * gracefully handles GPS failure without fabricating coordinates, and persists state idempotently.
     */
    fun markReachedSite() {
        val assignment = _uiState.value.assignment ?: return
        val gpid = assignment.idol.gpid

        if (_uiState.value.reachedSiteRecorded) {
            Timber.i("markReachedSite: already recorded for GPID %s", gpid)
            return
        }

        val status = LocationPermissions.checkSetupStatus(context)
        if (!status.isForegroundLocationGranted) {
            _uiState.value = _uiState.value.copy(
                reachedSiteError = "Location permission is required to record site arrival. Please grant permission above."
            )
            refreshPermissionState()
            return
        }

        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isRecordingReachedSite = true, reachedSiteError = null)
            val fix = locationClient.getCurrentLocation()
            val timeFormat = SimpleDateFormat("hh:mm:ss a", Locale.getDefault())
            val formattedTime = timeFormat.format(Date())
            val formattedCoords = if (fix != null) {
                String.format(Locale.US, "%.5f, %.5f", fix.latitude, fix.longitude)
            } else {
                null
            }

            prefs.edit()
                .putBoolean("reached_site_recorded_$gpid", true)
                .putString("reached_site_timestamp_$gpid", formattedTime)
                .apply {
                    if (formattedCoords != null) {
                        putString("reached_site_coords_$gpid", formattedCoords)
                    }
                }
                .apply()

            _uiState.value = _uiState.value.copy(
                isRecordingReachedSite = false,
                reachedSiteRecorded = true,
                reachedSiteTimestamp = formattedTime,
                reachedSiteCoordinates = formattedCoords,
                reachedSiteError = null,
            )
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
     * Start Procession gate. Submits fresh GPS fix and starts the foreground tracking session
     * once accepted by the backend.
     */
    fun startProcession() {
        if (_uiState.value.isStarting) return
        val assignment = _uiState.value.assignment ?: return
        if (_uiState.value.readiness !is ValidateProcessionStartUseCase.Result.Ready) return

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
                    _uiState.value = _uiState.value.copy(isStarting = false, startError = sessionResult.error.message)
                }
            }
        }
    }
}
