package com.ganeshvisarjan.fieldtracker.core.auth

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import dagger.hilt.android.qualifiers.ApplicationContext
import okhttp3.Cookie
import okhttp3.CookieJar
import okhttp3.HttpUrl
import javax.inject.Inject
import javax.inject.Singleton

/**
 * The Django backend uses cookie-based session authentication (SessionAuthentication,
 * not token/JWT — confirmed against config/settings/base.py), so this is what
 * "auth state persistence" means for this app: durably keep the sessionid +
 * csrftoken cookies across process death, encrypted at rest.
 *
 * OkHttp does not persist cookies on its own — without this, the officer would
 * be logged out every time the app process is killed.
 */
@Singleton
class SessionCookieJar @Inject constructor(@ApplicationContext context: Context) : CookieJar {

    private val masterKey = MasterKey.Builder(context)
        .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
        .build()

    private val prefs = EncryptedSharedPreferences.create(
        context,
        "session_cookies",
        masterKey,
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
    )

    private val memoryCache = mutableMapOf<String, List<Cookie>>()

    init {
        // Rehydrate from disk on cold start.
        prefs.all.forEach { (host, serialized) ->
            val raw = serialized as? String ?: return@forEach
            memoryCache[host] = raw.split("||").mapNotNull { Cookie.parse(HttpUrl.Builder().scheme("https").host(host).build(), it) }
        }
    }

    @Synchronized
    override fun saveFromResponse(url: HttpUrl, cookies: List<Cookie>) {
        if (cookies.isEmpty()) return
        val host = url.host
        val merged = (memoryCache[host].orEmpty() + cookies)
            .associateBy { it.name } // last write wins per cookie name
            .values
            .toList()
        memoryCache[host] = merged
        prefs.edit().putString(host, merged.joinToString("||") { it.toString() }).apply()
    }

    @Synchronized
    override fun loadForRequest(url: HttpUrl): List<Cookie> =
        memoryCache[url.host].orEmpty().filter { !it.expiresAt.let { exp -> exp in 1 until System.currentTimeMillis() } }

    @Synchronized
    fun clear() {
        memoryCache.clear()
        prefs.edit().clear().apply()
    }

    fun currentCsrfToken(host: String): String? =
        memoryCache[host]?.firstOrNull { it.name == "csrftoken" }?.value
}
