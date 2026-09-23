package com.ganeshvisarjan.fieldtracker.feature.home

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ganeshvisarjan.fieldtracker.core.network.ApiResult
import com.ganeshvisarjan.fieldtracker.domain.model.Assignment
import com.ganeshvisarjan.fieldtracker.domain.model.TrackingSession
import com.ganeshvisarjan.fieldtracker.domain.model.User
import com.ganeshvisarjan.fieldtracker.domain.repository.AssignmentRepository
import com.ganeshvisarjan.fieldtracker.domain.repository.AuthRepository
import com.ganeshvisarjan.fieldtracker.domain.repository.TrackingRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import javax.inject.Inject

import android.content.Context
import android.content.Intent
import com.ganeshvisarjan.fieldtracker.service.LocationTrackingService
import dagger.hilt.android.qualifiers.ApplicationContext

data class HomeUiState(
    val user: User? = null,
    val assignment: Assignment? = null,
    val activeSession: TrackingSession? = null,
    val isLoading: Boolean = true,
    val errorMessage: String? = null,
)

@HiltViewModel
class HomeViewModel @Inject constructor(
    @ApplicationContext private val context: Context,
    private val authRepository: AuthRepository,
    private val assignmentRepository: AssignmentRepository,
    private val trackingRepository: TrackingRepository,
) : ViewModel() {

    private val _assignmentState = MutableStateFlow<Assignment?>(null)
    private val _isLoading = MutableStateFlow(true)
    private val _errorMessage = MutableStateFlow<String?>(null)

    val uiState: StateFlow<HomeUiState> = combine(
        authRepository.currentUser,
        _assignmentState,
        trackingRepository.observeActiveSession(),
        _isLoading,
        _errorMessage,
    ) { user, assignment, session, loading, error ->
        HomeUiState(user = user, assignment = assignment, activeSession = session, isLoading = loading, errorMessage = error)
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), HomeUiState())

    init {
        loadAssignment()
    }

    fun loadAssignment() {
        viewModelScope.launch {
            _isLoading.value = true
            when (val result = assignmentRepository.getActiveAssignment()) {
                is ApiResult.Success -> {
                    val assignment = result.data
                    _assignmentState.value = assignment
                    _errorMessage.value = null
                    val activeSession = trackingRepository.getActiveSessionOnce()
                    if (activeSession != null) {
                        if (assignment == null || assignment.assignmentId != activeSession.assignmentId) {
                            // Backend confirms the assignment was ended / remotely terminated
                            trackingRepository.terminateSessionRemotely(activeSession.localSessionId)
                            val stopIntent = Intent(context, LocationTrackingService::class.java).apply {
                                action = LocationTrackingService.ACTION_STOP
                            }
                            context.startService(stopIntent)
                            _errorMessage.value = "Tracking was ended by an administrator."
                        }
                    }
                }
                is ApiResult.Error -> {
                    // Network error or server error - DO NOT infer termination! Keep local active session!
                    _errorMessage.value = result.error.message
                }
            }
            _isLoading.value = false
        }
    }

    fun clearErrorMessage() {
        _errorMessage.value = null
    }
}
