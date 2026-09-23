package com.ganeshvisarjan.fieldtracker.service

import com.ganeshvisarjan.fieldtracker.location.LocationFix
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import javax.inject.Inject
import javax.inject.Singleton

enum class ServiceRunState { STOPPED, STARTING, RUNNING }

/**
 * The service's observable state, injected into both the Service and the
 * ViewModel that reads it. This — not a static var on the Service class — is
 * the "source of truth" the spec asks for (section 13): a Hilt @Singleton
 * survives Activity recreation the same way, without the fragility of a raw
 * static field the Service might forget to clear.
 */
@Singleton
class TrackingServiceState @Inject constructor() {
    private val _runState = MutableStateFlow(ServiceRunState.STOPPED)
    val runState: StateFlow<ServiceRunState> = _runState

    private val _lastFix = MutableStateFlow<LocationFix?>(null)
    val lastFix: StateFlow<LocationFix?> = _lastFix

    private val _activeGpid = MutableStateFlow<String?>(null)
    val activeGpid: StateFlow<String?> = _activeGpid

    internal fun setRunState(state: ServiceRunState) { _runState.value = state }
    internal fun setLastFix(fix: LocationFix) { _lastFix.value = fix }
    internal fun setActiveGpid(gpid: String?) { _activeGpid.value = gpid }
}
