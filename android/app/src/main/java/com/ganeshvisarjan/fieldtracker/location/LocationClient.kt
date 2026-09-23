package com.ganeshvisarjan.fieldtracker.location

import android.annotation.SuppressLint
import android.content.Context
import com.ganeshvisarjan.fieldtracker.core.config.AppConfig
import dagger.hilt.android.qualifiers.ApplicationContext
import com.google.android.gms.location.CurrentLocationRequest
import com.google.android.gms.location.FusedLocationProviderClient
import com.google.android.gms.location.LocationCallback
import com.google.android.gms.location.LocationRequest
import com.google.android.gms.location.LocationResult
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import kotlinx.coroutines.tasks.await
import javax.inject.Inject
import javax.inject.Singleton

data class LocationFix(
    val latitude: Double,
    val longitude: Double,
    val accuracyMeters: Float?,
    val altitudeMeters: Double?,
    val speedMetersPerSecond: Float?,
    val bearingDegrees: Float?,
    val timestampMillis: Long,
)

/**
 * Thin wrapper over the Fused Location Provider. Callers are responsible for
 * having already checked permissions — this class does not request them
 * (spec section 12: request contextually from the UI, not buried in here).
 */
@Singleton
class LocationClient @Inject constructor(@ApplicationContext context: Context) {

    private val fusedClient: FusedLocationProviderClient =
        LocationServices.getFusedLocationProviderClient(context)

    /** One-shot fresh fix for the "Check Location" pre-start readiness screen. */
    @SuppressLint("MissingPermission")
    suspend fun getCurrentLocation(): LocationFix? {
        val request = CurrentLocationRequest.Builder()
            .setPriority(Priority.PRIORITY_HIGH_ACCURACY)
            .setMaxUpdateAgeMillis(0)
            .build()
        val location = fusedClient.getCurrentLocation(request, null).await() ?: return null
        return location.toFix()
    }

    /** Continuous stream for the foreground tracking service. Cancel the flow to stop updates. */
    @SuppressLint("MissingPermission")
    fun locationUpdates(): Flow<LocationFix> = callbackFlow {
        val request = LocationRequest.Builder(AppConfig.locationUpdateIntervalMs)
            .setPriority(Priority.PRIORITY_HIGH_ACCURACY)
            .setMinUpdateIntervalMillis(AppConfig.locationFastestIntervalMs)
            .setMinUpdateDistanceMeters(AppConfig.minDisplacementMeters)
            .build()

        val callback = object : LocationCallback() {
            override fun onLocationResult(result: LocationResult) {
                result.lastLocation?.toFix()?.let { trySend(it) }
            }
        }

        fusedClient.requestLocationUpdates(request, callback, null)
        awaitClose { fusedClient.removeLocationUpdates(callback) }
    }
}

private fun android.location.Location.toFix() = LocationFix(
    latitude = latitude,
    longitude = longitude,
    accuracyMeters = if (hasAccuracy()) accuracy else null,
    altitudeMeters = if (hasAltitude()) altitude else null,
    speedMetersPerSecond = if (hasSpeed()) speed else null,
    bearingDegrees = if (hasBearing()) bearing else null,
    timestampMillis = time,
)
