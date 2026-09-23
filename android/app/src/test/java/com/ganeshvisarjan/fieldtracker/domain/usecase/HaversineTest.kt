package com.ganeshvisarjan.fieldtracker.domain.usecase

import com.ganeshvisarjan.fieldtracker.domain.model.GeoPoint
import com.google.common.truth.Truth.assertThat
import org.junit.Test

/** Spec section 29 — boundary matrix for the 50m procession-start rule. */
class HaversineTest {

    private val hyderabad = GeoPoint(17.385044, 78.486671)

    @Test
    fun `same coordinates returns zero`() {
        assertThat(Haversine.distanceMeters(hyderabad, hyderabad)).isWithin(0.001).of(0.0)
    }

    @Test
    fun `known short distance is approximately correct`() {
        // ~0.001 degrees latitude at this longitude is close to 111 meters.
        val nearby = GeoPoint(hyderabad.latitude + 0.001, hyderabad.longitude)
        val distance = Haversine.distanceMeters(hyderabad, nearby)
        assertThat(distance).isWithin(2.0).of(111.19)
    }

    @Test
    fun `distance is symmetric`() {
        val other = GeoPoint(17.4, 78.5)
        assertThat(Haversine.distanceMeters(hyderabad, other))
            .isWithin(0.0001)
            .of(Haversine.distanceMeters(other, hyderabad))
    }

    @Test
    fun `antipodal-ish long distance is plausible`() {
        val farPoint = GeoPoint(-17.385044, -101.513329) // roughly opposite side of the globe
        val distance = Haversine.distanceMeters(hyderabad, farPoint)
        assertThat(distance).isGreaterThan(19_000_000.0) // sanity: large-scale distance, not a bug producing ~0
    }

    @Test(expected = IllegalArgumentException::class)
    fun `invalid latitude throws`() {
        GeoPoint(91.0, 78.0)
    }

    @Test(expected = IllegalArgumentException::class)
    fun `invalid longitude throws`() {
        GeoPoint(17.0, 181.0)
    }

    @Test
    fun `ofOrNull rejects NaN without throwing`() {
        assertThat(GeoPoint.ofOrNull(Double.NaN, 78.0)).isNull()
    }

    @Test
    fun `ofOrNull rejects out-of-range without throwing`() {
        assertThat(GeoPoint.ofOrNull(200.0, 78.0)).isNull()
    }
}
