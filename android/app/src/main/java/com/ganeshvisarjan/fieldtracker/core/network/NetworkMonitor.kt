package com.ganeshvisarjan.fieldtracker.core.network

import android.content.Context
import dagger.hilt.android.qualifiers.ApplicationContext
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.NetworkRequest
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import javax.inject.Inject
import javax.inject.Singleton

enum class NetworkState { ONLINE, OFFLINE, UNKNOWN }

/**
 * Single source of truth for connectivity (spec section 22). The Activity/UI
 * never polls this repeatedly on its own timer — the sync engine reacts to
 * transitions via WorkManager's own network constraint instead.
 */
@Singleton
class NetworkMonitor @Inject constructor(
    @ApplicationContext context: Context,
) {
    private val connectivityManager =
        context.applicationContext.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager

    private val scope = CoroutineScope(SupervisorJob())

    val state: StateFlow<NetworkState> = observe()
        .distinctUntilChanged()
        .stateIn(scope, SharingStarted.Eagerly, NetworkState.UNKNOWN)

    private fun observe(): Flow<NetworkState> = callbackFlow {
        val callback = object : ConnectivityManager.NetworkCallback() {
            override fun onAvailable(network: Network) {
                trySend(currentState())
            }

            override fun onLost(network: Network) {
                trySend(currentState())
            }

            override fun onCapabilitiesChanged(network: Network, capabilities: NetworkCapabilities) {
                trySend(currentState())
            }
        }

        val request = NetworkRequest.Builder()
            .addCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
            .build()

        connectivityManager.registerNetworkCallback(request, callback)
        trySend(currentState())

        awaitClose { connectivityManager.unregisterNetworkCallback(callback) }
    }

    private fun currentState(): NetworkState {
        val network = connectivityManager.activeNetwork ?: return NetworkState.OFFLINE
        val capabilities = connectivityManager.getNetworkCapabilities(network) ?: return NetworkState.OFFLINE
        val hasInternet = capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET) &&
            capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED)
        return if (hasInternet) NetworkState.ONLINE else NetworkState.OFFLINE
    }

    fun isOnline(): Boolean = currentState() == NetworkState.ONLINE
}
