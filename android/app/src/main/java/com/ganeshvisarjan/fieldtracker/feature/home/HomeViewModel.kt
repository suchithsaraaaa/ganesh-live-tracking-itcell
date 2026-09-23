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

data class HomeUiState(
    val user: User? = null,
    val assignment: Assignment? = null,
    val activeSession: TrackingSession? = null,
    val isLoading: Boolean = true,
    val errorMessage: String? = null,
)

@HiltViewModel
class HomeViewModel @Inject constructor(
    private val authRepository: AuthRepository,
    private val assignmentRepository: AssignmentRepository,
    trackingRepository: TrackingRepository,
) : ViewModel() {

    private val _assignmentState = MutableStateFlow<Assignment?>(null)
    private val _isLoading = MutableStateFlow(true)
    private val _errorMessage = MutableStateFlow<String?>(null)

    val uiState: StateFlow<HomeUiState> = combine(
        authRepository.currentUser,
        _assignmentState,
        trackingRepository.observeActiveSession(),
        _isLoading,
    ) { user, assignment, session, loading ->
        HomeUiState(user = user, assignment = assignment, activeSession = session, isLoading = loading, errorMessage = _errorMessage.value)
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), HomeUiState())

    init {
        loadAssignment()
    }

    fun loadAssignment() {
        viewModelScope.launch {
            _isLoading.value = true
            when (val result = assignmentRepository.getActiveAssignment()) {
                is ApiResult.Success -> {
                    _assignmentState.value = result.data
                    _errorMessage.value = null
                }
                is ApiResult.Error -> _errorMessage.value = result.error.message
            }
            _isLoading.value = false
        }
    }
}
