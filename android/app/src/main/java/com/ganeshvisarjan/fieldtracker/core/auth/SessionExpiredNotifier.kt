package com.ganeshvisarjan.fieldtracker.core.auth

import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import okhttp3.Interceptor
import okhttp3.Response
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Observes every response for a 401 and emits a single event the app can react
 * to centrally (clear local auth state, navigate to Login) instead of every
 * ViewModel independently checking for it.
 */
@Singleton
class SessionExpiredNotifier @Inject constructor() {
    private val _events = MutableSharedFlow<Unit>(extraBufferCapacity = 1)
    val events: SharedFlow<Unit> = _events

    fun notifySessionExpired() {
        _events.tryEmit(Unit)
    }
}

class UnauthorizedInterceptor @Inject constructor(
    private val notifier: SessionExpiredNotifier,
) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val response = chain.proceed(chain.request())
        if (response.code == 401) {
            notifier.notifySessionExpired()
        }
        return response
    }
}
