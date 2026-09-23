package com.ganeshvisarjan.fieldtracker.location

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.location.LocationManager
import android.os.Build
import android.os.PowerManager
import androidx.core.content.ContextCompat
import androidx.core.location.LocationManagerCompat

/**
 * Authoritative location and permission state machine for the field tracker application.
 * Normal procession tracking relies on foreground location (FINE/COARSE), active GPS
 * hardware services, and persistent service notifications.
 * ACCESS_BACKGROUND_LOCATION is deliberately NOT required.
 */
data class LocationSetupStatus(
    val hasFineLocation: Boolean,
    val hasCoarseLocation: Boolean,
    val isLocationServiceEnabled: Boolean,
    val hasNotificationPermission: Boolean,
    val isBatteryOptimizationIgnored: Boolean,
    val isPermanentlyDenied: Boolean = false,
) {
    /** True if high-accuracy GPS permission is granted. */
    val isPreciseGranted: Boolean get() = hasFineLocation

    /** True if officer granted approximate/coarse location only. */
    val isCoarseOnly: Boolean get() = hasCoarseLocation && !hasFineLocation

    /** True if any foreground location permission is granted. */
    val isForegroundLocationGranted: Boolean get() = hasFineLocation || hasCoarseLocation

    /**
     * True when all prerequisites for continuous procession tracking are satisfied:
     * - Precise location granted
     * - Android Location Services / GPS enabled on device
     * - Persistent tracking notification permission granted (Android 13+)
     */
    val isFullyReady: Boolean
        get() = hasFineLocation && isLocationServiceEnabled && hasNotificationPermission

    /** Returns the next missing setup action required to guide the officer. */
    val nextRequiredAction: NextSetupAction
        get() = when {
            isPermanentlyDenied -> NextSetupAction.OPEN_APP_SETTINGS
            !isForegroundLocationGranted -> NextSetupAction.REQUEST_FOREGROUND_PERMISSION
            !hasFineLocation -> NextSetupAction.REQUEST_PRECISE_PERMISSION
            !isLocationServiceEnabled -> NextSetupAction.ENABLE_LOCATION_SERVICES
            !hasNotificationPermission -> NextSetupAction.REQUEST_NOTIFICATION_PERMISSION
            !isBatteryOptimizationIgnored -> NextSetupAction.OPTIMIZE_BATTERY
            else -> NextSetupAction.NONE
        }
}

enum class NextSetupAction {
    NONE,
    REQUEST_FOREGROUND_PERMISSION,
    REQUEST_PRECISE_PERMISSION,
    ENABLE_LOCATION_SERVICES,
    REQUEST_NOTIFICATION_PERMISSION,
    OPTIMIZE_BATTERY,
    OPEN_APP_SETTINGS,
}

object LocationPermissions {

    fun hasFineLocation(context: Context): Boolean =
        ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED

    fun hasCoarseLocation(context: Context): Boolean =
        ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED

    fun hasPreciseLocation(context: Context): Boolean = hasFineLocation(context)

    fun hasNotifications(context: Context): Boolean =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED
        } else {
            true // Pre-Tiramisu: notifications are enabled by default
        }

    fun isLocationEnabled(context: Context): Boolean {
        val lm = context.getSystemService(Context.LOCATION_SERVICE) as? LocationManager ?: return false
        return LocationManagerCompat.isLocationEnabled(lm)
    }

    fun isBatteryOptimizationIgnored(context: Context): Boolean {
        val pm = context.getSystemService(Context.POWER_SERVICE) as? PowerManager ?: return true
        return pm.isIgnoringBatteryOptimizations(context.packageName)
    }

    /** Authoritative snapshot of all location, permission, and hardware readiness states. */
    fun checkSetupStatus(context: Context, isPermanentlyDenied: Boolean = false): LocationSetupStatus =
        LocationSetupStatus(
            hasFineLocation = hasFineLocation(context),
            hasCoarseLocation = hasCoarseLocation(context),
            isLocationServiceEnabled = isLocationEnabled(context),
            hasNotificationPermission = hasNotifications(context),
            isBatteryOptimizationIgnored = isBatteryOptimizationIgnored(context),
            isPermanentlyDenied = isPermanentlyDenied,
        )

    val foregroundPermissions: Array<String> = arrayOf(
        Manifest.permission.ACCESS_FINE_LOCATION,
        Manifest.permission.ACCESS_COARSE_LOCATION,
    )

    val notificationPermission: Array<String> =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            arrayOf(Manifest.permission.POST_NOTIFICATIONS)
        } else {
            emptyArray()
        }
}
