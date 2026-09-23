package com.ganeshvisarjan.fieldtracker.core.config

import com.ganeshvisarjan.fieldtracker.BuildConfig

/**
 * Which data sources this build talks to. Selected at compile time by the Gradle
 * product flavor (mock / dev / staging / prod — see app/build.gradle.kts), never
 * by a runtime toggle a field officer could flip. [AppModule] reads this to decide
 * whether to bind the mock or real repository implementations — nothing else in
 * the app (ViewModels, UI, sync engine) needs to know which one is active.
 */
enum class AppEnvironment {
    MOCK,
    DEVELOPMENT,
    STAGING,
    PRODUCTION;

    val usesMockApi: Boolean get() = this == MOCK

    companion object {
        val current: AppEnvironment
            get() = when {
                BuildConfig.USE_MOCK_API -> MOCK
                BuildConfig.FLAVOR == "dev" -> DEVELOPMENT
                BuildConfig.FLAVOR == "staging" -> STAGING
                else -> PRODUCTION
            }
    }
}

/** Central home for the small set of business-tunable constants BuildConfig exposes. */
object AppConfig {
    val apiBaseUrl: String get() = BuildConfig.API_BASE_URL
    // No processionStartMaxDistanceMeters — the 50m proximity-to-idol-origin
    // requirement was removed from the Android start flow (2026-09-23 product
    // decision); see ValidateProcessionStartUseCase.
    val gpsAccuracyThresholdMeters: Float get() = BuildConfig.GPS_ACCURACY_THRESHOLD_METERS.toFloat()
    val locationUpdateIntervalMs: Long get() = BuildConfig.LOCATION_UPDATE_INTERVAL_MS
    val locationFastestIntervalMs: Long get() = BuildConfig.LOCATION_FASTEST_INTERVAL_MS
    val minDisplacementMeters: Float get() = BuildConfig.MIN_DISPLACEMENT_METERS
    val telemetryBatchSize: Int get() = BuildConfig.TELEMETRY_BATCH_SIZE
    val debugScreenEnabled: Boolean get() = BuildConfig.DEBUG_SCREEN_ENABLED
    val verboseLogging: Boolean get() = BuildConfig.VERBOSE_LOGGING
}
