package com.ganeshvisarjan.fieldtracker.core.network

import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import retrofit2.HttpException
import java.io.IOException
import java.net.SocketTimeoutException
import java.net.UnknownHostException

/** Matches the `{"error": "...", ...other fields}` shape every confirmed backend business rejection uses (e.g. StartTrackingView's START_GATE_REJECTED body). */
@Serializable
private data class BackendErrorBody(val error: String? = null)

private val errorBodyJson = Json { ignoreUnknownKeys = true; isLenient = true }

/** Centralizes HTTP-status → [ApiError] mapping (spec section 34) so it's not repeated per-repository. */
object ApiErrorMapper {

    fun from(throwable: Throwable): ApiError = when (throwable) {
        is SocketTimeoutException -> ApiError.Timeout()
        is UnknownHostException -> ApiError.NetworkUnavailable()
        is IOException -> ApiError.NetworkUnavailable()
        is HttpException -> fromHttpCode(throwable.code(), backendErrorMessage(throwable) ?: throwable.message())
        else -> ApiError.Unknown(throwable.message ?: "Something went wrong.")
    }

    /**
     * [HttpException.message] is Retrofit's generic HTTP status line (e.g.
     * "HTTP 400 Bad Request"), NOT the response body — so a confirmed backend
     * business rejection (e.g. `{"error": "START_GATE_REJECTED: Officer is
     * 65.0m away..."}` from `StartTrackingView`) would otherwise never reach
     * the officer. Per the requirement to display the backend's actual
     * business error rather than a generic one, this reads the real error body.
     */
    private fun backendErrorMessage(exception: HttpException): String? {
        val body = try {
            exception.response()?.errorBody()?.string()
        } catch (_: Exception) {
            null
        } ?: return null
        return try {
            errorBodyJson.decodeFromString(BackendErrorBody.serializer(), body).error
        } catch (_: Exception) {
            null
        }
    }

    private fun fromHttpCode(code: Int, message: String?): ApiError = when (code) {
        400 -> ApiError.BadRequest(message ?: "Invalid request.")
        401 -> ApiError.Unauthorized()
        403 -> ApiError.Forbidden()
        404 -> ApiError.NotFound()
        409 -> ApiError.Conflict(message ?: "This action conflicts with the current state.")
        429 -> ApiError.RateLimited()
        in 500..599 -> ApiError.ServerError()
        else -> ApiError.Unknown(message ?: "Unexpected response ($code).")
    }
}

/** Runs [block], wrapping any thrown exception into an [ApiResult.Error] via [ApiErrorMapper]. */
suspend inline fun <T> safeApiCall(crossinline block: suspend () -> T): ApiResult<T> = try {
    ApiResult.Success(block())
} catch (t: Throwable) {
    ApiResult.Error(ApiErrorMapper.from(t))
}
