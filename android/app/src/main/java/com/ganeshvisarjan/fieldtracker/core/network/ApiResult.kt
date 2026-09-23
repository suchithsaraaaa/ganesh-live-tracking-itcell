package com.ganeshvisarjan.fieldtracker.core.network

/**
 * Structured outcome for every repository call that hits the network (spec
 * section 34). ViewModels convert [ApiError] into a human-readable message —
 * raw JSON/HTTP detail never reaches the field officer directly.
 */
sealed class ApiResult<out T> {
    data class Success<T>(val data: T) : ApiResult<T>()
    data class Error(val error: ApiError) : ApiResult<Nothing>()
}

sealed class ApiError(open val message: String) {
    data class BadRequest(override val message: String) : ApiError(message)
    data class Unauthorized(override val message: String = "Session expired. Please log in again.") : ApiError(message)
    data class Forbidden(override val message: String = "You do not have permission for this action.") : ApiError(message)
    data class NotFound(override val message: String = "Requested resource was not found.") : ApiError(message)
    data class Conflict(override val message: String) : ApiError(message)
    data class RateLimited(override val message: String = "Too many requests. Please wait a moment.") : ApiError(message)
    data class ServerError(override val message: String = "The server encountered an error. Please try again.") : ApiError(message)
    data class NetworkUnavailable(override val message: String = "No network connection.") : ApiError(message)
    data class Timeout(override val message: String = "The request timed out.") : ApiError(message)
    data class Unknown(override val message: String = "Something went wrong.") : ApiError(message)

    /** Structured backend business-rule rejection, e.g. an assignment/procession-start rule the backend enforces. */
    data class BusinessRuleViolation(override val message: String, val code: String? = null) : ApiError(message)
}

inline fun <T> ApiResult<T>.onSuccess(block: (T) -> Unit): ApiResult<T> {
    if (this is ApiResult.Success) block(data)
    return this
}

inline fun <T> ApiResult<T>.onError(block: (ApiError) -> Unit): ApiResult<T> {
    if (this is ApiResult.Error) block(error)
    return this
}

fun <T> ApiResult<T>.getOrNull(): T? = (this as? ApiResult.Success)?.data
