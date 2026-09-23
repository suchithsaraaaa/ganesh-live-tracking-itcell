package com.ganeshvisarjan.fieldtracker.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import com.ganeshvisarjan.fieldtracker.MainActivity
import com.ganeshvisarjan.fieldtracker.R
import com.ganeshvisarjan.fieldtracker.core.logging.TrackingLog
import com.ganeshvisarjan.fieldtracker.domain.model.GeoPoint
import com.ganeshvisarjan.fieldtracker.domain.repository.TrackingRepository
import com.ganeshvisarjan.fieldtracker.domain.usecase.ServiceRestartDecision
import com.ganeshvisarjan.fieldtracker.location.LocationClient
import com.ganeshvisarjan.fieldtracker.worker.SyncScheduler
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking
import javax.inject.Inject

/**
 * Foreground GPS collection service (spec sections 13, 38). Started ONLY by an
 * explicit user action (never on boot, never silently — see AndroidManifest,
 * no BOOT_COMPLETED receiver registered for this). Does not depend on any
 * Activity remaining alive; state is published through [TrackingServiceState],
 * not read back from the Activity.
 *
 * Room ([TrackingRepository], backed by [com.ganeshvisarjan.fieldtracker.data.local.dao.TrackingSessionDao])
 * is the sole authority for "is a session currently active" — not
 * [TrackingServiceState] (that's an in-memory observable mirror for the UI,
 * reset every process start) and not a static var on this class. This matters
 * because [onStartCommand] can legitimately be re-invoked with a null [Intent]
 * — see "Foreground service recovery" below.
 */
@AndroidEntryPoint
class LocationTrackingService : Service() {

    @Inject lateinit var locationClient: LocationClient
    @Inject lateinit var trackingRepository: TrackingRepository
    @Inject lateinit var serviceState: TrackingServiceState
    @Inject lateinit var syncScheduler: SyncScheduler

    private val serviceScope = CoroutineScope(SupervisorJob())
    private var collectionJob: Job? = null

    override fun onBind(intent: Intent?): IBinder? = null

    /**
     * Foreground service recovery (audit scenarios C/D/E). `START_STICKY`
     * means the system can restart this service after it was killed — but the
     * restart [Intent] is null, so [EXTRA_SESSION_LOCAL_ID]/[EXTRA_GPID] from
     * the original `ACTION_START` are gone. A foreground service must call
     * [startForeground] promptly after any [onStartCommand] invocation or the
     * system can kill/crash the process (the FGS timing contract on Android
     * 9+), so this resolves synchronously — a local Room read on an
     * already-open connection is fast enough to do inline here, and there is
     * no safe way to defer this decision to a later coroutine resumption.
     */
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_START -> {
                val sessionLocalId = intent.getStringExtra(EXTRA_SESSION_LOCAL_ID)
                val gpid = intent.getStringExtra(EXTRA_GPID)
                if (sessionLocalId != null && gpid != null) {
                    startTracking(sessionLocalId, gpid)
                }
            }
            ACTION_STOP -> stopTracking()
            null -> handleNullIntentRestart()
        }
        return START_STICKY
    }

    /**
     * Scenario C: an ACTIVE session exists in Room → resume it (never create a
     * new one — [startTracking] only starts GPS collection, it never inserts a
     * [com.ganeshvisarjan.fieldtracker.data.local.entity.TrackingSessionEntity]).
     * Scenario D: no session at all → do nothing, stop immediately.
     * Scenario E: the session is STOP_REQUESTED/STOPPED/anything but ACTIVE
     * (the officer already asked to stop) → do not resume GPS collection.
     * The actual decision is pure logic in [ServiceRestartDecision]
     * (unit-tested there); this just supplies the Room read and acts on it.
     */
    private fun handleNullIntentRestart() {
        val active = runBlocking { trackingRepository.observeActiveSession().first() }
        when (val action = ServiceRestartDecision.decide(active)) {
            is ServiceRestartDecision.Action.Resume -> startTracking(action.sessionLocalId, action.gpid)
            ServiceRestartDecision.Action.DoNothing -> stopSelf()
        }
    }

    private fun startTracking(sessionLocalId: String, gpid: String) {
        // Avoid creating a duplicate collection job if already running (spec section 13).
        if (collectionJob?.isActive == true) return

        serviceState.setActiveGpid(gpid)
        serviceState.setRunState(ServiceRunState.STARTING)
        startForeground(NOTIFICATION_ID, buildNotification(gpid))

        collectionJob = serviceScope.launch {
            serviceState.setRunState(ServiceRunState.RUNNING)
            locationClient.locationUpdates().collect { fix ->
                serviceState.setLastFix(fix)
                val point = GeoPoint.ofOrNull(fix.latitude, fix.longitude) ?: return@collect
                trackingRepository.recordTelemetryPoint(
                    sessionLocalId = sessionLocalId,
                    gpid = gpid,
                    location = point,
                    accuracyMeters = fix.accuracyMeters,
                    altitudeMeters = fix.altitudeMeters,
                    speedMetersPerSecond = fix.speedMetersPerSecond,
                    bearingDegrees = fix.bearingDegrees,
                    recordedAt = fix.timestampMillis,
                )
                // Nudge the sync worker rather than uploading per-point (spec section 39/18).
                syncScheduler.scheduleTelemetrySync()
            }
        }
    }

    private fun stopTracking() {
        collectionJob?.cancel()
        collectionJob = null
        serviceState.setRunState(ServiceRunState.STOPPED)
        serviceState.setActiveGpid(null)
        TrackingLog.sessionStopped("service-stopped")
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    override fun onDestroy() {
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
            .setContentTitle(getString(R.string.tracking_notification_title))
            // GPID only — no owner name/phone/other PII on a notification that
            // could surface on a locked screen (spec section 38).
            .setContentText("GPID: $gpid")
            .setSmallIcon(android.R.drawable.ic_menu_mylocation)
            .setOngoing(true)
            .setContentIntent(contentIntent)
            .setPriority(NotificationCompat.PRIORITY_LOW)
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
