package com.ganeshvisarjan.fieldtracker.worker

import android.content.Context
import dagger.hilt.android.qualifiers.ApplicationContext
import androidx.work.BackoffPolicy
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkRequest
import java.util.concurrent.TimeUnit
import javax.inject.Inject
import javax.inject.Singleton

/**
 * The only place WorkManager requests get built (spec section 18/49) — both the
 * foreground service (after each point) and the UI (after Stop Tracking) call
 * through here rather than constructing WorkRequests themselves.
 */
@Singleton
class SyncScheduler @Inject constructor(
    @ApplicationContext private val context: Context,
) {
    private val workManager get() = WorkManager.getInstance(context)

    private val networkConstraint = Constraints.Builder()
        .setRequiredNetworkType(NetworkType.CONNECTED)
        .build()

    fun scheduleTelemetrySync() {
        val request = OneTimeWorkRequestBuilder<TelemetrySyncWorker>()
            .setConstraints(networkConstraint)
            .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, WorkRequest.MIN_BACKOFF_MILLIS, TimeUnit.MILLISECONDS)
            .build()
        // KEEP: a burst of GPS fixes shouldn't queue N duplicate sync jobs.
        workManager.enqueueUniqueWork(WORK_TELEMETRY_SYNC, ExistingWorkPolicy.KEEP, request)
    }

    fun scheduleProcessionEventSync() {
        val request = OneTimeWorkRequestBuilder<ProcessionEventSyncWorker>()
            .setConstraints(networkConstraint)
            .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, WorkRequest.MIN_BACKOFF_MILLIS, TimeUnit.MILLISECONDS)
            .build()
        workManager.enqueueUniqueWork(WORK_EVENT_SYNC, ExistingWorkPolicy.KEEP, request)
    }

    /** Called once tracking stops, to drain the queue promptly and then finalize the session. */
    fun scheduleImmediateFullSync() {
        scheduleTelemetrySync()
        scheduleProcessionEventSync()
    }

    /**
     * Safety net for spec test scenario G (network down for 30+ min, no new GPS
     * fix ever fires to re-enqueue a sync). 15 minutes is WorkManager's minimum
     * periodic interval. Idempotent — call once at app startup.
     */
    fun schedulePeriodicSafetyNet() {
        val request = PeriodicWorkRequestBuilder<TelemetrySyncWorker>(15, TimeUnit.MINUTES)
            .setConstraints(networkConstraint)
            .build()
        workManager.enqueueUniquePeriodicWork(WORK_PERIODIC_SAFETY_NET, ExistingPeriodicWorkPolicy.KEEP, request)
    }

    companion object {
        private const val WORK_TELEMETRY_SYNC = "telemetry_sync"
        private const val WORK_EVENT_SYNC = "procession_event_sync"
        private const val WORK_PERIODIC_SAFETY_NET = "telemetry_sync_periodic"
    }
}
