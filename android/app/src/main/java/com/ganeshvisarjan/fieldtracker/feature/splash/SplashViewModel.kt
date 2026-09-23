package com.ganeshvisarjan.fieldtracker.feature.splash

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ganeshvisarjan.fieldtracker.domain.repository.AuthRepository
import com.ganeshvisarjan.fieldtracker.domain.repository.AuthState
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class SplashViewModel @Inject constructor(
    private val authRepository: AuthRepository,
) : ViewModel() {

    private val _resolvedState = MutableStateFlow<AuthState?>(null)
    val resolvedState: StateFlow<AuthState?> = _resolvedState.asStateFlow()

    init {
        viewModelScope.launch {
            authRepository.refreshCurrentUser()
            _resolvedState.value = authRepository.authState.value
        }
    }
}
