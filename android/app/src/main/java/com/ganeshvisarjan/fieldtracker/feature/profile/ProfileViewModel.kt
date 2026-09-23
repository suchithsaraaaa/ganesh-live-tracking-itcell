package com.ganeshvisarjan.fieldtracker.feature.profile

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ganeshvisarjan.fieldtracker.domain.model.User
import com.ganeshvisarjan.fieldtracker.domain.repository.AuthRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ProfileUiState(val user: User? = null, val loggedOut: Boolean = false)

@HiltViewModel
class ProfileViewModel @Inject constructor(
    private val authRepository: AuthRepository,
) : ViewModel() {

    private val _loggedOut = MutableStateFlow(false)

    val uiState: StateFlow<ProfileUiState> = combine(authRepository.currentUser, _loggedOut) { user, loggedOut ->
        ProfileUiState(user, loggedOut)
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), ProfileUiState())

    fun logout() {
        viewModelScope.launch {
            authRepository.logout()
            _loggedOut.value = true
        }
    }
}
