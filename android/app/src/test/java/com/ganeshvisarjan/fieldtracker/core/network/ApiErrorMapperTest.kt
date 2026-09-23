package com.ganeshvisarjan.fieldtracker.core.network

import com.google.common.truth.Truth.assertThat
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Test
import retrofit2.HttpException
import retrofit2.Response

/**
 * Integration-hardening audit (2026-09-23): [HttpException.message] is Retrofit's
 * generic HTTP status line, not the response body — these tests guard against
 * regressing back to that generic message instead of the confirmed backend's
 * actual business-rule text (e.g. StartTrackingView's `{"error": "START_GATE_REJECTED: ..."}`).
 */
class ApiErrorMapperTest {

    @Test
    fun `a 400 response with a backend error body surfaces that exact message`() {
        val body = """{"error":"START_GATE_REJECTED: Officer is 65.0m away from authoritative idol origin (maximum allowed: 50.0m).","distance_meters":65.0}"""
        val exception = HttpException(Response.error<Any>(400, body.toResponseBody(null)))

        val error = ApiErrorMapper.from(exception)

        assertThat(error).isInstanceOf(ApiError.BadRequest::class.java)
        assertThat(error.message).isEqualTo(
            "START_GATE_REJECTED: Officer is 65.0m away from authoritative idol origin (maximum allowed: 50.0m).",
        )
    }

    @Test
    fun `a 400 response with an unparseable body falls back to a generic message rather than crashing`() {
        val exception = HttpException(Response.error<Any>(400, "not json".toResponseBody(null)))

        val error = ApiErrorMapper.from(exception)

        assertThat(error).isInstanceOf(ApiError.BadRequest::class.java)
        assertThat(error.message).isNotEmpty()
    }

    @Test
    fun `a 409 response also surfaces the backend's real error text`() {
        val body = """{"error":"This session has already been stopped."}"""
        val exception = HttpException(Response.error<Any>(409, body.toResponseBody(null)))

        val error = ApiErrorMapper.from(exception)

        assertThat(error).isInstanceOf(ApiError.Conflict::class.java)
        assertThat(error.message).isEqualTo("This session has already been stopped.")
    }

    @Test
    fun `a 500 response ignores the body and uses the generic server error message`() {
        val body = """{"error":"internal traceback should never reach the officer"}"""
        val exception = HttpException(Response.error<Any>(500, body.toResponseBody(null)))

        val error = ApiErrorMapper.from(exception)

        assertThat(error).isInstanceOf(ApiError.ServerError::class.java)
    }
}
