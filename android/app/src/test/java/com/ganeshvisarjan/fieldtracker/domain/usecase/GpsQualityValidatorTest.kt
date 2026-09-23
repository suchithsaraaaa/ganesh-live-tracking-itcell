package com.ganeshvisarjan.fieldtracker.domain.usecase

import com.ganeshvisarjan.fieldtracker.domain.model.GeoPoint
import com.google.common.truth.Truth.assertThat
import org.junit.Test

/** Spec section 15 — quality gate must reject bad fixes without ever adjusting a good one. */
class GpsQualityValidatorTest {

    private val validator = GpsQualityValidator()
    private val point = GeoPoint(17.4, 78.5)

    @Test
    fun `accepts a normal fix`() {
        assertThat(validator.isAcceptable(point, 8f)).isTrue()
    }

    @Test
    fun `rejects a null point`() {
        assertThat(validator.isAcceptable(null, 8f)).isFalse()
    }

    @Test
    fun `rejects zero accuracy`() {
        assertThat(validator.isAcceptable(point, 0f)).isFalse()
    }

    @Test
    fun `rejects negative accuracy`() {
        assertThat(validator.isAcceptable(point, -5f)).isFalse()
    }

    @Test
    fun `rejects NaN accuracy`() {
        assertThat(validator.isAcceptable(point, Float.NaN)).isFalse()
    }

    @Test
    fun `rejects wildly inaccurate fix`() {
        assertThat(validator.isAcceptable(point, 500f)).isFalse()
    }

    @Test
    fun `accepts a fix with unknown accuracy`() {
        assertThat(validator.isAcceptable(point, null)).isTrue()
    }

    @Test
    fun `flags a near-identical fix as duplicate`() {
        val almostSame = GeoPoint(point.latitude + 0.00001, point.longitude)
        assertThat(validator.isDuplicate(point, almostSame, minDisplacementMeters = 5f)).isTrue()
    }

    @Test
    fun `does not flag a materially different fix as duplicate`() {
        val moved = GeoPoint(point.latitude + 0.01, point.longitude)
        assertThat(validator.isDuplicate(point, moved, minDisplacementMeters = 5f)).isFalse()
    }

    @Test
    fun `first fix in a session is never a duplicate`() {
        assertThat(validator.isDuplicate(null, point, minDisplacementMeters = 5f)).isFalse()
    }
}
