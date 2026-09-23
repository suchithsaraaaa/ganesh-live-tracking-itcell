package com.ganeshvisarjan.fieldtracker.data.repository

import com.ganeshvisarjan.fieldtracker.core.auth.SessionCookieJar
import com.ganeshvisarjan.fieldtracker.core.network.ApiResult
import com.ganeshvisarjan.fieldtracker.core.network.getOrNull
import com.ganeshvisarjan.fieldtracker.core.network.safeApiCall
import com.ganeshvisarjan.fieldtracker.data.remote.api.AuthApi
import com.ganeshvisarjan.fieldtracker.data.remote.dto.LoginRequestDto
import com.ganeshvisarjan.fieldtracker.data.remote.dto.UserDto
import com.ganeshvisarjan.fieldtracker.domain.model.Role
import com.ganeshvisarjan.fieldtracker.domain.model.User
import com.ganeshvisarjan.fieldtracker.domain.repository.AuthRepository
import com.ganeshvisarjan.fieldtracker.domain.repository.AuthState
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import javax.inject.Inject
import javax.inject.Singleton

private fun UserDto.toDomain(): User = User(
    id = id,
    username = username,
    displayName = username, // backend has no separate display_name field today
    role = Role.fromRaw(role),
    policeStation = policeStation,
    zone = zone,
    division = division,
)

@Singleton
class AuthRepositoryImpl @Inject constructor(
    private val api: AuthApi,
    private val cookieJar: SessionCookieJar,
) : AuthRepository {

    private val _authState = MutableStateFlow(AuthState.LOADING)
    override val authState: StateFlow<AuthState> = _authState

    private val _currentUser = MutableStateFlow<User?>(null)
    override val currentUser: StateFlow<User?> = _currentUser

    override suspend fun login(username: String, password: String): ApiResult<User> {
        val result = safeApiCall { api.login(LoginRequestDto(username, password)).toDomain() }
        result.getOrNull()?.let {
            _currentUser.value = it
            _authState.value = AuthState.AUTHENTICATED
        }
        return result
    }

    override suspend fun logout() {
        // Best-effort: clear local state regardless of whether the network call
        // succeeds, so the officer is never stuck "logged in" on-device because
        // of a connectivity blip or a backend CSRF rejection (see CsrfInterceptor).
        safeApiCall { api.logout() }
        cookieJar.clear()
        _currentUser.value = null
        _authState.value = AuthState.UNAUTHENTICATED
    }

    override suspend fun refreshCurrentUser(): ApiResult<User> {
        val result = safeApiCall { api.currentUser().toDomain() }
        when (result) {
            is ApiResult.Success -> {
                _currentUser.value = result.data
                _authState.value = AuthState.AUTHENTICATED
            }
            is ApiResult.Error -> {
                _currentUser.value = null
                _authState.value = AuthState.UNAUTHENTICATED
            }
        }
        return result
    }

    override fun isAuthenticated(): Boolean = _authState.value == AuthState.AUTHENTICATED
}
