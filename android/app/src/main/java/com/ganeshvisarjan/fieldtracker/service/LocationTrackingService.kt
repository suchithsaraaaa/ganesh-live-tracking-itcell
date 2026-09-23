package com.ganeshvisarjan.fieldtracker.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat
import com.ganeshvisarjan.fieldtracker.MainActivity
import com.ganeshvisarjan.fieldtracker.R
import com.ganeshvisarjan.fieldtracker.core.logging.TrackingLog
import com.ganeshvisarjan.fieldtracker.domain.model.GeoPoint
import com.ganeshvisarjan.fieldtracker.domain.repository.TrackingRepository
import com.ganeshvisarjan.fieldtracker.domain.usecase.ServiceRestartDecision
import com.ganeshvisarjan.fieldtracker.location.LocationClient
import com.ganeshvisarjan.fieldtracker.worker.SyncScheduler
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.CoroutineExceptionHandler
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import timber.log.Timber
import javax.inject.Inject

/**
 * Foreground GPS collection service. Started ONLY by an explicit user action
 * (never on boot, never silently). Does not depend on any Activity remaining alive;
 * state is published through [TrackingServiceState].
 *
 * Uses Android 14+ FOREGROUND_SERVICE_TYPE_LOCATION and a leak-proof partial WakeLock
 * to ensure continuous GPS telemetry when the phone screen is locked or app is backgrounded.
 */
@AndroidEntryPoint
class LocationTrackingService : Service() {

    @Inject lateinit var locationClient: LocationClient
    @Inject lateinit var trackingRepository: TrackingRepository
    @Inject lateinit var serviceState: TrackingServiceState
    @Inject lateinit var syncScheduler: SyncScheduler

    private val serviceScope = CoroutineScope(
        SupervisorJob() + Dispatchers.Main.immediate + CoroutineExceptionHandler { _, throwable ->
            Timber.e(throwable, "LocationTrackingService uncaught coroutine exception")
        }
    )
    private var collectionJob: Job? = null
    private var wakeLock: PowerManager.WakeLock? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_START -> {
                val sessionLocalId = intent.getStringExtra(EXTRA_SESSION_LOCAL_ID)
                val gpid = intent.getStringExtra(EXTRA_GPID) ?: serviceState.activeGpid.value ?: "Field Duty"
                startTracking(sessionLocalId, gpid)
            }
            ACTION_STOP -> stopTracking()
            null -> handleNullIntentRestart()
        }
        return START_STICKY
    }

    private fun handleNullIntentRestart() {
        // Immediately satisfy Android's foreground service start contract
        val fallbackGpid = serviceState.activeGpid.value ?: "Procession"
        safeStartForeground(fallbackGpid)
        serviceScope.launch {
            val active = trackingRepository.observeActiveSession().first()
            when (val action = ServiceRestartDecision.decide(active)) {
                is ServiceRestartDecision.Action.Resume -> startTracking(action.sessionLocalId, action.gpid)
                ServiceRestartDecision.Action.DoNothing -> stopSelf()
            }
        }
    }

    private fun safeStartForeground(gpid: String) {
        val notification = buildNotification(gpid)
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                ServiceCompat.startForeground(
                    this,
                    NOTIFICATION_ID,
                    notification,
                    ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION,
                )
            } else {
                startForeground(NOTIFICATION_ID, notification)
            }
        } catch (e: Exception) {
            Timber.e(e, "Exception in safeStartForeground for GPID %s", gpid)
        }
    }

    private fun startTracking(sessionLocalId: String?, gpid: String) {
        serviceState.setActiveGpid(gpid)
        // Satisfy the Android foreground service timer immediately on every START call
        safeStartForeground(gpid)

        if (sessionLocalId == null) {
            Timber.w("startTracking called without sessionLocalId for GPID %s — notification shown", gpid)
            return
        }

        if (collectionJob?.isActive == true) {
            Timber.i("Collection job already active for GPID %s — service notification updated", gpid)
            return
        }

        serviceState.setRunState(ServiceRunState.STARTING)
        acquireWakeLock()

        collectionJob = serviceScope.launch {
            serviceState.setRunState(ServiceRunState.RUNNING)
            locationClient.locationUpdates()
                .catch { e ->
                    Timber.e(e, "Error streaming location fixes in LocationTrackingService")
                }
                .collect { fix ->
                    val active = trackingRepository.getActiveSessionOnce()
                    if (active == null || active.localSessionId != sessionLocalId) {
                        Timber.w("Session %s is no longer active - stopping collection", sessionLocalId)
                        stopTracking()
                        return@collect
                    }
                    serviceState.setLastFix(fix)
                    val point = GeoPoint.ofOrNull(fix.latitude, fix.longitude) ?: return@collect
                    val recorded = trackingRepository.recordTelemetryPoint(
                        sessionLocalId = sessionLocalId,
                        gpid = gpid,
                        location = point,
                        accuracyMeters = fix.accuracyMeters,
                        altitudeMeters = fix.altitudeMeters,
                        speedMetersPerSecond = fix.speedMetersPerSecond,
                        bearingDegrees = fix.bearingDegrees,
                        recordedAt = fix.timestampMillis,
                    )
                    if (recorded) {
                        syncScheduler.scheduleTelemetrySync()
                    }
                }
        }
    }

    private fun acquireWakeLock() {
        if (wakeLock?.isHeld == true) return
        try {
            val powerManager = getSystemService(Context.POWER_SERVICE) as? PowerManager
            wakeLock = powerManager?.newWakeLock(
                PowerManager.PARTIAL_WAKE_LOCK,
                "TGPolice:LocationTrackingWakeLock",
            )?.apply {
                setReferenceCounted(false)
                acquire(12 * 60 * 60 * 1000L) // 12-hour safe ceiling
            }
            Timber.i("Acquired partial WakeLock for procession tracking")
        } catch (e: Exception) {
            Timber.w(e, "Failed to acquire WakeLock")
        }
    }

    private fun releaseWakeLock() {
        try {
            if (wakeLock?.isHeld == true) {
                wakeLock?.release()
                Timber.i("Released partial WakeLock")
            }
        } catch (e: Exception) {
            Timber.w(e, "Error releasing WakeLock")
        } finally {
            wakeLock = null
        }
    }

    private fun stopTracking() {
        releaseWakeLock()
        collectionJob?.cancel()
        collectionJob = null
        serviceState.setRunState(ServiceRunState.STOPPED)
        serviceState.setActiveGpid(null)
        TrackingLog.sessionStopped("service-stopped")
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    override fun onDestroy() {
        releaseWakeLock()
        collectionJob?.cancel()
        serviceScope.cancel()
        serviceState.setRunState(ServiceRunState.STOPPED)
        super.onDestroy()
    }

    private fun buildNotification(gpid: String): Notification {
        ensureChannel()
        val contentIntent = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("TG Police Visarjan Tracker")
            .setContentText("Procession tracking active")
            .setSubText("GPID: $gpid")
            .setSmallIcon(android.R.drawable.ic_menu_mylocation)
            .setOngoing(true)
            .setContentIntent(contentIntent)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setCategory(NotificationCompat.CATEGORY_SERVICE)
            .build()
    }

    private fun ensureChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val manager = getSystemService(NotificationManager::class.java)
        if (manager.getNotificationChannel(CHANNEL_ID) != null) return
        val channel = NotificationChannel(
            CHANNEL_ID,
            getString(R.string.notification_channel_tracking),
            NotificationManager.IMPORTANCE_LOW,
        ).apply {
            description = getString(R.string.notification_channel_tracking_desc)
        }
        manager.createNotificationChannel(channel)
    }

    companion object {
        const val ACTION_START = "com.ganeshvisarjan.fieldtracker.action.START_TRACKING"
        const val ACTION_STOP = "com.ganeshvisarjan.fieldtracker.action.STOP_TRACKING"
        const val EXTRA_SESSION_LOCAL_ID = "extra_session_local_id"
        const val EXTRA_GPID = "extra_gpid"
        private const val CHANNEL_ID = "tracking_channel"
        private const val NOTIFICATION_ID = 4201
    }
}
