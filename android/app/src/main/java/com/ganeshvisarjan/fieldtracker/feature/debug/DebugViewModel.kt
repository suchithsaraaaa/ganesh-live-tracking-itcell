package com.ganeshvisarjan.fieldtracker.feature.debug

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ganeshvisarjan.fieldtracker.core.config.AppConfig
import com.ganeshvisarjan.fieldtracker.core.config.AppEnvironment
import com.ganeshvisarjan.fieldtracker.core.network.NetworkMonitor
import com.ganeshvisarjan.fieldtracker.domain.repository.AuthRepository
import com.ganeshvisarjan.fieldtracker.domain.repository.TrackingRepository
import com.ganeshvisarjan.fieldtracker.service.TrackingServiceState
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import javax.inject.Inject

data class DebugUiState(
    val environment: String = AppEnvironment.current.name,
    val apiBaseUrl: String = AppConfig.apiBaseUrl,
    val isAuthenticated: Boolean = false,
    val activeGpid: String? = null,
    val activeSessionId: String? = null,
    val lastFixAccuracy: Float? = null,
    val lastFixTimestamp: Long? = null,
    val pendingTelemetry: Int = 0,
    val networkState: String = "UNKNOWN",
)

/** Spec section 36 — never shown in release builds; see NavGraph gating on AppConfig.debugScreenEnabled. */
@HiltViewModel
class DebugViewModel @Inject constructor(
    authRepository: AuthRepository,
    trackingRepository: TrackingRepository,
    serviceState: TrackingServiceState,
    networkMonitor: NetworkMonitor,
) : ViewModel() {

    val uiState: StateFlow<DebugUiState> = combine(
        authRepository.authState,
        trackingRepository.observeActiveSession(),
        trackingRepository.observePendingTelemetryCount(),
        serviceState.lastFix,
        networkMonitor.state,
    ) { authState, session, pending, fix, network ->
        DebugUiState(
            isAuthenticated = authState.name == "AUTHENTICATED",
            activeGpid = session?.gpid,
            activeSessionId = session?.serverSessionId ?: session?.localSessionId,
            lastFixAccuracy = fix?.accuracyMeters,
            lastFixTimestamp = fix?.timestampMillis,
            pendingTelemetry = pending,
            networkState = network.name,
        )
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), DebugUiState())
}
