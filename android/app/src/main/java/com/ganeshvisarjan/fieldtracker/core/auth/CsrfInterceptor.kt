package com.ganeshvisarjan.fieldtracker.core.auth

import okhttp3.Interceptor
import okhttp3.Response
import javax.inject.Inject

/**
 * Mirrors the same convention implemented on the React dashboard: echo the
 * csrftoken cookie back as X-CSRFToken on any unsafe method, since Django's
 * SessionAuthentication enforces CSRF once a session exists.
 *
 * KNOWN BACKEND GAP (confirmed while building the web dashboard): Django's
 * CSRF_TRUSTED_ORIGINS is not set in config/settings/base.py, so the backend
 * currently rejects authenticated POSTs with "Origin checking failed" even
 * when this header is sent correctly. This is a backend settings fix, not
 * something either client can work around — see docs/API_CONTRACT.md.
 */
class CsrfInterceptor @Inject constructor(
    private val cookieJar: SessionCookieJar,
) : Interceptor {

    private val unsafeMethods = setOf("POST", "PUT", "PATCH", "DELETE")

    override fun intercept(chain: Interceptor.Chain): Response {
        val original = chain.request()
        if (original.method !in unsafeMethods) return chain.proceed(original)

        val token = cookieJar.currentCsrfToken(original.url.host) ?: return chain.proceed(original)
        val withCsrf = original.newBuilder()
            .header("X-CSRFToken", token)
            .build()
        return chain.proceed(withCsrf)
    }
}
