package com.ganeshvisarjan.fieldtracker.worker

import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.ganeshvisarjan.fieldtracker.core.network.ApiResult
import com.ganeshvisarjan.fieldtracker.domain.repository.ProcessionRepository
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject

/** Uploads queued procession events in chronological order (spec section 24). */
@HiltWorker
class ProcessionEventSyncWorker @AssistedInject constructor(
    @Assisted context: Context,
    @Assisted params: WorkerParameters,
    private val processionRepository: ProcessionRepository,
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result = when (processionRepository.syncPendingEvents()) {
        is ApiResult.Success -> Result.success()
        is ApiResult.Error -> if (runAttemptCount < MAX_ATTEMPTS) Result.retry() else Result.failure()
    }

    companion object {
        private const val MAX_ATTEMPTS = 8
    }
}
