package com.ganeshvisarjan.fieldtracker.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class LoginRequestDto(
    val username: String,
    val password: String,
)

/** Mirrors LoginView/CurrentUserView response shape in apps/accounts/views.py. */
@Serializable
data class UserDto(
    val id: Int,
    val username: String,
    val role: String,
    @SerialName("police_id") val policeId: String? = null,
    val zone: String? = null,
    val division: String? = null,
    @SerialName("police_station") val policeStation: String? = null,
)
