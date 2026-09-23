package com.ganeshvisarjan.fieldtracker.domain.model

/** A validated lat/lon pair. Construction is the only place invalid coordinates are rejected. */
data class GeoPoint(val latitude: Double, val longitude: Double) {
    init {
        require(!latitude.isNaN() && !longitude.isNaN()) { "GeoPoint coordinates must not be NaN" }
        require(latitude in -90.0..90.0) { "Latitude out of range: $latitude" }
        require(longitude in -180.0..180.0) { "Longitude out of range: $longitude" }
    }

    companion object {
        /** Returns null instead of throwing — use at input boundaries (GPS callback, DTO mapping). */
        fun ofOrNull(latitude: Double?, longitude: Double?): GeoPoint? {
            if (latitude == null || longitude == null) return null
            if (latitude.isNaN() || longitude.isNaN()) return null
            if (latitude !in -90.0..90.0) return null
            if (longitude !in -180.0..180.0) return null
            return GeoPoint(latitude, longitude)
        }
    }
}
