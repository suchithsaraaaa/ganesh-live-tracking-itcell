package com.ganeshvisarjan.fieldtracker.feature.tracking

import android.content.Context
import android.content.Intent
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ganeshvisarjan.fieldtracker.core.network.ApiResult
import com.ganeshvisarjan.fieldtracker.core.network.NetworkMonitor
import com.ganeshvisarjan.fieldtracker.core.network.NetworkState
import com.ganeshvisarjan.fieldtracker.domain.model.Assignment
import com.ganeshvisarjan.fieldtracker.domain.model.GeoPoint
import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionEventRecord
import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionEventType
import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionState
import com.ganeshvisarjan.fieldtracker.domain.model.TrackingSession
import com.ganeshvisarjan.fieldtracker.domain.repository.AssignmentRepository
import com.ganeshvisarjan.fieldtracker.domain.repository.ProcessionRepository
import com.ganeshvisarjan.fieldtracker.domain.repository.TrackingRepository
import com.ganeshvisarjan.fieldtracker.domain.usecase.ProcessionStateMachine
import com.ganeshvisarjan.fieldtracker.location.LocationClient
import com.ganeshvisarjan.fieldtracker.location.LocationFix
import com.ganeshvisarjan.fieldtracker.service.LocationTrackingService
import com.ganeshvisarjan.fieldtracker.service.ServiceRunState
import com.ganeshvisarjan.fieldtracker.service.TrackingServiceState
import com.ganeshvisarjan.fieldtracker.worker.SyncScheduler
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import timber.log.Timber
import javax.inject.Inject

data class TrackingUiState(
    val session: TrackingSession? = null,
    val assignment: Assignment? = null,
    val processionState: ProcessionState? = null,
    val timeline: List<ProcessionEventRecord> = emptyList(),
    val lastFix: LocationFix? = null,
    val serviceRunning: Boolean = false,
    val networkState: NetworkState = NetworkState.UNKNOWN,
    val pendingTelemetryCount: Int = 0,
    val pendingEventCount: Int = 0,
    val isSubmittingAction: Boolean = false,
    val actionError: String? = null,
    val isRemotelyTerminated: Boolean = false,
) {
    val availableActions: Set<ProcessionEventType>
        get() = processionState?.let { ProcessionStateMachine.availableEvents(it) } ?: emptySet()
}

@OptIn(kotlinx.coroutines.ExperimentalCoroutinesApi::class)
@HiltViewModel
class TrackingViewModel @Inject constructor(
    @ApplicationContext private val context: Context,
    private val trackingRepository: TrackingRepository,
    private val processionRepository: ProcessionRepository,
    private val assignmentRepository: AssignmentRepository,
    private val locationClient: LocationClient,
    networkMonitor: NetworkMonitor,
    private val serviceState: TrackingServiceState,
    private val syncScheduler: SyncScheduler,
) : ViewModel() {

    private val _isSubmittingAction = MutableStateFlow(false)
    private val _actionError = MutableStateFlow<String?>(null)
    private val _assignment = MutableStateFlow<Assignment?>(null)
    private val _isRemotelyTerminated = MutableStateFlow(false)
    private var assignmentId: String? = null

    private val sessionFlow = trackingRepository.observeActiveSession()

    private val processionFlow = sessionFlow.flatMapLatest { session ->
        if (session == null) flowOf<Pair<ProcessionState?, List<ProcessionEventRecord>>>(null to emptyList())
        else combine(
            processionRepository.observeState(session.gpid),
            processionRepository.observeTimeline(session.gpid),
        ) { state, timeline -> state to timeline }
    }

    val uiState: StateFlow<TrackingUiState> = combine(
        sessionFlow,
        _assignment,
        processionFlow,
        serviceState.runState,
        serviceState.lastFix,
    ) { session, assignment, procession, runState, lastFix ->
        BaseState(
            session = session,
            assignment = assignment,
            processionState = procession.first,
            timeline = procession.second,
            serviceRunning = runState == ServiceRunState.RUNNING,
            lastFix = lastFix,
        )
    }.combine(networkMonitor.state) { base, network ->
        base to network
    }.combine(trackingRepository.observePendingTelemetryCount()) { (base, network), pendingTelemetry ->
        Triple(base, network, pendingTelemetry)
    }.combine(processionRepository.observePendingEventCount()) { (base, network, pendingTelemetry), pendingEvents ->
        Counts(base, network, pendingTelemetry, pendingEvents)
    }.combine(_isSubmittingAction) { counts, submitting ->
        counts to submitting
    }.combine(_actionError) { (counts, submitting), error ->
        Triple(counts, submitting, error)
    }.combine(_isRemotelyTerminated) { (counts, submitting, error), remotelyTerminated ->
        TrackingUiState(
            session = counts.base.session,
            assignment = counts.base.assignment,
            processionState = counts.base.processionState,
            timeline = counts.base.timeline,
            lastFix = counts.base.lastFix,
            serviceRunning = counts.base.serviceRunning,
            networkState = counts.network,
            pendingTelemetryCount = counts.pendingTelemetry,
            pendingEventCount = counts.pendingEvents,
            isSubmittingAction = submitting,
            actionError = error,
            isRemotelyTerminated = remotelyTerminated,
        )
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), TrackingUiState())

    private data class BaseState(
        val session: TrackingSession?,
        val assignment: Assignment?,
        val processionState: ProcessionState?,
        val timeline: List<ProcessionEventRecord>,
        val serviceRunning: Boolean,
        val lastFix: LocationFix?,
    )

    private data class Counts(
        val base: BaseState,
        val network: NetworkState,
        val pendingTelemetry: Int,
        val pendingEvents: Int,
    )

    init {
        loadAssignment()
        startPeriodicAssignmentCheck()
    }

    fun loadAssignment() {
        viewModelScope.launch {
            when (val result = assignmentRepository.getActiveAssignment()) {
                is ApiResult.Success -> {
                    val active = result.data
                    _assignment.value = active
                    assignmentId = active?.assignmentId
                    val currentSession = trackingRepository.getActiveSessionOnce()
                    if (currentSession != null && (active == null || active.assignmentId != currentSession.assignmentId)) {
                        trackingRepository.terminateSessionRemotely(currentSession.localSessionId)
                        val stopIntent = Intent(context, LocationTrackingService::class.java).apply {
                            action = LocationTrackingService.ACTION_STOP
                        }
                        context.startService(stopIntent)
                        _isRemotelyTerminated.value = true
                        syncScheduler.scheduleImmediateFullSync()
                    }
                }
                is ApiResult.Error -> {
                    Timber.w("Failed to load active assignment: %s", result.error.message)
                }
            }
        }
    }

    private fun startPeriodicAssignmentCheck() {
        viewModelScope.launch {
            while (isActive) {
                delay(8_000L)
                val activeSession = trackingRepository.getActiveSessionOnce() ?: break
                when (val result = assignmentRepository.getActiveAssignment()) {
                    is ApiResult.Success -> {
                        val active = result.data
                        if (active == null || active.assignmentId != activeSession.assignmentId) {
                            trackingRepository.terminateSessionRemotely(activeSession.localSessionId)
                            val stopIntent = Intent(context, LocationTrackingService::class.java).apply {
                                action = LocationTrackingService.ACTION_STOP
                            }
                            context.startService(stopIntent)
                            _isRemotelyTerminated.value = true
                            syncScheduler.scheduleImmediateFullSync()
                            break
                        }
                    }
                    is ApiResult.Error -> {
                        // Network error: preserve local active session
                    }
                }
            }
        }
    }

    fun acknowledgeRemoteTermination() {
        _isRemotelyTerminated.value = false
    }

    fun ensureServiceStarted(sessionLocalId: String, gpid: String) {
        val intent = Intent(context, LocationTrackingService::class.java).apply {
            action = LocationTrackingService.ACTION_START
            putExtra(LocationTrackingService.EXTRA_SESSION_LOCAL_ID, sessionLocalId)
            putExtra(LocationTrackingService.EXTRA_GPID, gpid)
        }
        context.startForegroundService(intent)
    }

    fun submitAction(eventType: ProcessionEventType) {
        val session = uiState.value.session ?: return
        val assignment = assignmentId ?: session.assignmentId
        if (_isSubmittingAction.value) return

        viewModelScope.launch {
            _isSubmittingAction.value = true
            _actionError.value = null

            val fix = serviceState.lastFix.value ?: locationClient.getCurrentLocation()
            val location = fix?.let { GeoPoint.ofOrNull(it.latitude, it.longitude) }
            if (location == null) {
                _actionError.value = "Acquiring GPS fix... please try again."
                _isSubmittingAction.value = false
                return@launch
            }

            val result = processionRepository.submitEvent(session.gpid, assignment, session.localSessionId, eventType, location)
            if (result is ApiResult.Error) {
                _actionError.value = result.error.message
            }
            _isSubmittingAction.value = false
        }
    }

    fun clearActionError() {
        _actionError.value = null
    }

    /** Spec section 24: mark stop-requested locally (works offline) and let sync finalize it. */
    fun stopTracking() {
        val session = uiState.value.session ?: return
        viewModelScope.launch {
            trackingRepository.requestStopSession(session.localSessionId)
            context.startService(
                Intent(context, LocationTrackingService::class.java).apply {
                    action = LocationTrackingService.ACTION_STOP
                },
            )
            syncScheduler.scheduleImmediateFullSync()
        }
    }
}
