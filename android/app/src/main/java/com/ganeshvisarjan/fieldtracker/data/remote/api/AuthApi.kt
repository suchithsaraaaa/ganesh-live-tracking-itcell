package com.ganeshvisarjan.fieldtracker.data.remote.api

import com.ganeshvisarjan.fieldtracker.data.remote.ApiEndpoints
import com.ganeshvisarjan.fieldtracker.data.remote.dto.LoginRequestDto
import com.ganeshvisarjan.fieldtracker.data.remote.dto.UserDto
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST

interface AuthApi {
    @POST(ApiEndpoints.LOGIN)
    suspend fun login(@Body request: LoginRequestDto): UserDto

    @POST(ApiEndpoints.LOGOUT)
    suspend fun logout()

    @GET(ApiEndpoints.CURRENT_USER)
    suspend fun currentUser(): UserDto
}
