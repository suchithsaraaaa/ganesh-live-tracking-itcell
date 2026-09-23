package com.ganeshvisarjan.fieldtracker.domain.usecase

import com.ganeshvisarjan.fieldtracker.domain.model.GeoPoint
import javax.inject.Inject

/**
 * Quality gate applied to every raw GPS fix before it is persisted (spec section
 * 15). This only rejects fixes — it never adjusts, smooths, or otherwise
 * fabricates a coordinate. What passes through is exactly what the device
 * reported.
 */
class GpsQualityValidator @Inject constructor() {

    /** A generous ceiling (not the procession-start threshold) — reject only clearly-unusable fixes. */
    private val maxAcceptableAccuracyMeters = 200f

    fun isAcceptable(point: GeoPoint?, accuracyMeters: Float?): Boolean {
        if (point == null) return false
        if (accuracyMeters != null && (accuracyMeters.isNaN() || accuracyMeters <= 0f)) return false
        if (accuracyMeters != null && accuracyMeters > maxAcceptableAccuracyMeters) return false
        return true
    }

    /** True if [candidate] is materially the same fix as [previous] and can be safely skipped. */
    fun isDuplicate(previous: GeoPoint?, candidate: GeoPoint, minDisplacementMeters: Float): Boolean {
        if (previous == null) return false
        return Haversine.distanceMeters(previous, candidate) < minDisplacementMeters
    }
}
