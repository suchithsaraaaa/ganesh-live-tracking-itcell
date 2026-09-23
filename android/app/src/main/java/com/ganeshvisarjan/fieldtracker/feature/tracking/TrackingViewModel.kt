package com.ganeshvisarjan.fieldtracker.feature.tracking

import android.content.Context
import android.content.Intent
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ganeshvisarjan.fieldtracker.core.network.ApiResult
import com.ganeshvisarjan.fieldtracker.core.network.NetworkMonitor
import com.ganeshvisarjan.fieldtracker.core.network.NetworkState
import com.ganeshvisarjan.fieldtracker.domain.model.GeoPoint
import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionEventRecord
import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionEventType
import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionState
import com.ganeshvisarjan.fieldtracker.domain.model.TrackingSession
import com.ganeshvisarjan.fieldtracker.domain.repository.AssignmentRepository
import com.ganeshvisarjan.fieldtracker.domain.repository.ProcessionRepository
import com.ganeshvisarjan.fieldtracker.domain.repository.TrackingRepository
import com.ganeshvisarjan.fieldtracker.domain.usecase.ProcessionStateMachine
import com.ganeshvisarjan.fieldtracker.location.LocationFix
import com.ganeshvisarjan.fieldtracker.service.LocationTrackingService
import com.ganeshvisarjan.fieldtracker.service.ServiceRunState
import com.ganeshvisarjan.fieldtracker.service.TrackingServiceState
import com.ganeshvisarjan.fieldtracker.worker.SyncScheduler
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import javax.inject.Inject

data class TrackingUiState(
    val session: TrackingSession? = null,
    val processionState: ProcessionState? = null,
    val timeline: List<ProcessionEventRecord> = emptyList(),
    val lastFix: LocationFix? = null,
    val serviceRunning: Boolean = false,
    val networkState: NetworkState = NetworkState.UNKNOWN,
    val pendingTelemetryCount: Int = 0,
    val pendingEventCount: Int = 0,
    val isSubmittingAction: Boolean = false,
    val actionError: String? = null,
) {
    val availableActions: Set<ProcessionEventType>
        get() = processionState?.let { ProcessionStateMachine.availableEvents(it) } ?: emptySet()
}

@HiltViewModel
class TrackingViewModel @Inject constructor(
    @ApplicationContext private val context: Context,
    private val trackingRepository: TrackingRepository,
    private val processionRepository: ProcessionRepository,
    private val assignmentRepository: AssignmentRepository,
    networkMonitor: NetworkMonitor,
    private val serviceState: TrackingServiceState,
    private val syncScheduler: SyncScheduler,
) : ViewModel() {

    private val _isSubmittingAction = MutableStateFlow(false)
    private val _actionError = MutableStateFlow<String?>(null)
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
        processionFlow,
        serviceState.runState,
        serviceState.lastFix,
        networkMonitor.state,
    ) { session, procession, runState, lastFix, network ->
        BaseState(session, procession.first, procession.second, runState == ServiceRunState.RUNNING, lastFix, network)
    }.combine(trackingRepository.observePendingTelemetryCount()) { base, pendingTelemetry ->
        base to pendingTelemetry
    }.combine(processionRepository.observePendingEventCount()) { (base, pendingTelemetry), pendingEvents ->
        base to (pendingTelemetry to pendingEvents)
    }.combine(_isSubmittingAction) { (base, counts), submitting ->
        Triple(base, counts, submitting)
    }.combine(_actionError) { (base, counts, submitting), error ->
        TrackingUiState(
            session = base.session,
            processionState = base.processionState,
            timeline = base.timeline,
            lastFix = base.lastFix,
            serviceRunning = base.serviceRunning,
            networkState = base.networkState,
            pendingTelemetryCount = counts.first,
            pendingEventCount = counts.second,
            isSubmittingAction = submitting,
            actionError = error,
        )
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), TrackingUiState())

    private data class BaseState(
        val session: TrackingSession?,
        val processionState: ProcessionState?,
        val timeline: List<ProcessionEventRecord>,
        val serviceRunning: Boolean,
        val lastFix: LocationFix?,
        val networkState: NetworkState,
    )

    init {
        viewModelScope.launch {
            assignmentId = (assignmentRepository.getActiveAssignment() as? ApiResult.Success)?.data?.assignmentId
        }
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
        val assignment = assignmentId ?: return
        val fix = serviceState.lastFix.value
        val location = fix?.let { GeoPoint.ofOrNull(it.latitude, it.longitude) }
        if (location == null) {
            _actionError.value = "No GPS fix yet — wait a moment and try again."
            return
        }

        viewModelScope.launch {
            _isSubmittingAction.value = true
            _actionError.value = null
            val result = processionRepository.submitEvent(session.gpid, assignment, session.localSessionId, eventType, location)
            if (result is ApiResult.Error) {
                _actionError.value = result.error.message
            }
            _isSubmittingAction.value = false
        }
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
