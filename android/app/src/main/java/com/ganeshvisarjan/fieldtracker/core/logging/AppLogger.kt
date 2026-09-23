package com.ganeshvisarjan.fieldtracker.core.logging

import com.ganeshvisarjan.fieldtracker.core.config.AppConfig
import timber.log.Timber

/**
 * Structured event tags for the tracking pipeline (spec section 35). Never log
 * passwords, tokens, Authorization headers, or full phone numbers through this —
 * these are operational breadcrumbs, not an audit trail.
 */
object TrackingLog {
    private const val TAG = "TrackingService"

    fun gpsFix(accuracy: Float?) = Timber.tag(TAG).d("GPS_FIX accuracy=%.1fm", accuracy ?: -1f)
    fun pointStored(localId: Long) = Timber.tag(TAG).d("POINT_STORED id=%d", localId)
    fun syncStarted(count: Int) = Timber.tag(TAG).d("SYNC_STARTED pending=%d", count)
    fun syncSuccess(count: Int) = Timber.tag(TAG).d("SYNC_SUCCESS uploaded=%d", count)
    fun syncFailure(reason: String) = Timber.tag(TAG).w("SYNC_FAILURE reason=%s", reason)
    fun sessionStarted(sessionId: String) = Timber.tag(TAG).i("SESSION_STARTED id=%s", sessionId)
    fun sessionStopped(sessionId: String) = Timber.tag(TAG).i("SESSION_STOPPED id=%s", sessionId)
}

/** A [Timber.Tree] that only plants in debug builds and never on release (spec section 35). */
object AppLogger {
    fun init() {
        if (AppConfig.verboseLogging) {
            Timber.plant(Timber.DebugTree())
        }
    }
}
