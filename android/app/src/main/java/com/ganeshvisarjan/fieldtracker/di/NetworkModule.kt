package com.ganeshvisarjan.fieldtracker.di

import com.ganeshvisarjan.fieldtracker.core.auth.CsrfInterceptor
import com.ganeshvisarjan.fieldtracker.core.auth.SessionCookieJar
import com.ganeshvisarjan.fieldtracker.core.auth.SessionExpiredNotifier
import com.ganeshvisarjan.fieldtracker.core.auth.UnauthorizedInterceptor
import com.ganeshvisarjan.fieldtracker.core.config.AppConfig
import com.ganeshvisarjan.fieldtracker.data.remote.api.AssignmentApi
import com.ganeshvisarjan.fieldtracker.data.remote.api.AuthApi
import com.ganeshvisarjan.fieldtracker.data.remote.api.ProcessionApi
import com.ganeshvisarjan.fieldtracker.data.remote.api.TrackingApi
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import timber.log.Timber
import java.util.concurrent.TimeUnit
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {

    @Provides
    @Singleton
    fun provideJson(): Json = Json {
        ignoreUnknownKeys = true
        isLenient = true
        explicitNulls = false
    }

    // SessionCookieJar, SessionExpiredNotifier, NetworkMonitor, and CsrfInterceptor
    // all carry their own @Inject constructor (see core/auth, core/network) — Hilt
    // provides them from that directly; declaring @Provides here too would create
    // a duplicate binding.

    @Provides
    @Singleton
    fun provideOkHttpClient(
        cookieJar: SessionCookieJar,
        csrfInterceptor: CsrfInterceptor,
        sessionExpiredNotifier: SessionExpiredNotifier,
    ): OkHttpClient {
        val logging = HttpLoggingInterceptor { message ->
            // Redact anything that looks like a credential/cookie/auth header before it
            // ever reaches Logcat (spec section 35) — bodies still show structurally,
            // but never in release builds, since the level below is only set in debug.
            if (AppConfig.verboseLogging) {
                val redacted = message
                    .replace(Regex("\"password\"\\s*:\\s*\".*?\""), "\"password\":\"[REDACTED]\"")
                    .replace(Regex("(?i)(cookie|authorization|x-csrftoken):.*"), "$1: [REDACTED]")
                Timber.tag("OkHttp").d(redacted)
            }
        }.apply {
            level = if (AppConfig.verboseLogging) HttpLoggingInterceptor.Level.BODY else HttpLoggingInterceptor.Level.NONE
        }

        return OkHttpClient.Builder()
            .cookieJar(cookieJar)
            .addInterceptor(csrfInterceptor)
            .addInterceptor(UnauthorizedInterceptor(sessionExpiredNotifier))
            .addInterceptor(logging)
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .build()
    }

    @Provides
    @Singleton
    fun provideRetrofit(okHttpClient: OkHttpClient, json: Json): Retrofit {
        val contentType = "application/json".toMediaType()
        return Retrofit.Builder()
            .baseUrl(AppConfig.apiBaseUrl)
            .client(okHttpClient)
            .addConverterFactory(json.asConverterFactory(contentType))
            .build()
    }

    @Provides
    @Singleton
    fun provideAuthApi(retrofit: Retrofit): AuthApi = retrofit.create(AuthApi::class.java)

    @Provides
    @Singleton
    fun provideAssignmentApi(retrofit: Retrofit): AssignmentApi = retrofit.create(AssignmentApi::class.java)

    @Provides
    @Singleton
    fun provideTrackingApi(retrofit: Retrofit): TrackingApi = retrofit.create(TrackingApi::class.java)

    @Provides
    @Singleton
    fun provideProcessionApi(retrofit: Retrofit): ProcessionApi = retrofit.create(ProcessionApi::class.java)
}
