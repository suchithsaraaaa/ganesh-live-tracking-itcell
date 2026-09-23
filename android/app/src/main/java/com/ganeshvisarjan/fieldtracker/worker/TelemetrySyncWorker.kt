package com.ganeshvisarjan.fieldtracker.worker

import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.ganeshvisarjan.fieldtracker.core.network.ApiResult
import com.ganeshvisarjan.fieldtracker.domain.repository.TrackingRepository
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject

/**
 * Drains the local telemetry queue in [com.ganeshvisarjan.fieldtracker.core.config.AppConfig.telemetryBatchSize]
 * batches, then finalizes a STOP_REQUESTED session once its queue is empty
 * (spec sections 18, 24). Re-enqueues itself while points remain, so a large
 * backlog (spec test scenario E, 100+ points) drains across several runs
 * instead of one long-lived worker execution.
 */
@HiltWorker
class TelemetrySyncWorker @AssistedInject constructor(
    @Assisted context: Context,
    @Assisted params: WorkerParameters,
    private val trackingRepository: TrackingRepository,
    private val syncScheduler: SyncScheduler,
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        return when (val result = trackingRepository.syncPendingTelemetry()) {
            is ApiResult.Success -> {
                if (result.data > 0) {
                    // More may remain beyond this batch — schedule another pass.
                    syncScheduler.scheduleTelemetrySync()
                }
                trackingRepository.finalizeStopIfReady()
                Result.success()
            }
            is ApiResult.Error -> {
                if (runAttemptCount < MAX_ATTEMPTS) Result.retry() else Result.failure()
            }
        }
    }

    companion object {
        private const val MAX_ATTEMPTS = 8
    }
}
