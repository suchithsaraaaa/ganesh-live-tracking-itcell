package com.ganeshvisarjan.fieldtracker.location

import android.annotation.SuppressLint
import android.content.Context
import android.os.Looper
import com.ganeshvisarjan.fieldtracker.core.config.AppConfig
import com.google.android.gms.location.CurrentLocationRequest
import com.google.android.gms.location.FusedLocationProviderClient
import com.google.android.gms.location.LocationCallback
import com.google.android.gms.location.LocationRequest
import com.google.android.gms.location.LocationResult
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import kotlinx.coroutines.tasks.await
import timber.log.Timber
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
 * Robust wrapper over the Fused Location Provider. Callers are responsible for
 * requesting permissions from the UI. This class explicitly verifies permissions
 * before making any Google Play Services calls and defensively handles
 * SecurityException so the process never terminates on ungranted permissions.
 */
@Singleton
class LocationClient @Inject constructor(
    @ApplicationContext private val context: Context,
) {

    private val fusedClient: FusedLocationProviderClient =
        LocationServices.getFusedLocationProviderClient(context)

    /** One-shot fresh fix for the "Check Location" pre-start readiness screen. */
    @SuppressLint("MissingPermission")
    suspend fun getCurrentLocation(): LocationFix? {
        if (!LocationPermissions.hasFineLocation(context) && !LocationPermissions.hasCoarseLocation(context)) {
            Timber.w("getCurrentLocation invoked without granted location permission — returning null safely")
            return null
        }
        return try {
            val request = CurrentLocationRequest.Builder()
                .setPriority(Priority.PRIORITY_HIGH_ACCURACY)
                .setMaxUpdateAgeMillis(0)
                .build()
            val location = fusedClient.getCurrentLocation(request, null).await() ?: return null
            location.toFix()
        } catch (e: SecurityException) {
            Timber.w(e, "SecurityException in getCurrentLocation — handled defensively")
            null
        } catch (e: Exception) {
            Timber.e(e, "Exception in getCurrentLocation")
            null
        }
    }

    /** Continuous stream for the foreground tracking service. Cancel the flow to stop updates. */
    @SuppressLint("MissingPermission")
    fun locationUpdates(): Flow<LocationFix> = callbackFlow {
        if (!LocationPermissions.hasFineLocation(context) && !LocationPermissions.hasCoarseLocation(context)) {
            Timber.w("locationUpdates invoked without granted location permission — closing flow safely")
            close()
            return@callbackFlow
        }

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

        try {
            fusedClient.requestLocationUpdates(request, callback, Looper.getMainLooper())
        } catch (e: SecurityException) {
            Timber.w(e, "SecurityException in requestLocationUpdates — handled defensively")
            close()
            return@callbackFlow
        } catch (e: Exception) {
            Timber.e(e, "Exception in requestLocationUpdates — handled defensively")
            close()
            return@callbackFlow
        }

        awaitClose {
            try {
                fusedClient.removeLocationUpdates(callback)
            } catch (e: Exception) {
                Timber.w(e, "Exception in removeLocationUpdates")
            }
        }
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
