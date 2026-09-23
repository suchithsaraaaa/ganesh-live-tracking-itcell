package com.ganeshvisarjan.fieldtracker.data.mock

import com.ganeshvisarjan.fieldtracker.core.network.ApiError
import com.ganeshvisarjan.fieldtracker.core.network.ApiResult
import com.ganeshvisarjan.fieldtracker.domain.model.User
import com.ganeshvisarjan.fieldtracker.domain.repository.AuthRepository
import com.ganeshvisarjan.fieldtracker.domain.repository.AuthState
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import javax.inject.Inject
import javax.inject.Singleton

/** Accepts any non-blank username/password so UI/manual testing never blocks on a real backend. */
@Singleton
class MockAuthRepository @Inject constructor() : AuthRepository {

    private val _authState = MutableStateFlow(AuthState.UNAUTHENTICATED)
    override val authState: StateFlow<AuthState> = _authState

    private val _currentUser = MutableStateFlow<User?>(null)
    override val currentUser: StateFlow<User?> = _currentUser

    override suspend fun login(username: String, password: String): ApiResult<User> {
        delay(400)
        if (username.isBlank() || password.isBlank()) {
            return ApiResult.Error(ApiError.BadRequest("Username and password required."))
        }
        _currentUser.value = MockData.officer.copy(username = username)
        _authState.value = AuthState.AUTHENTICATED
        return ApiResult.Success(_currentUser.value!!)
    }

    override suspend fun logout() {
        delay(150)
        _currentUser.value = null
        _authState.value = AuthState.UNAUTHENTICATED
    }

    override suspend fun refreshCurrentUser(): ApiResult<User> {
        val user = _currentUser.value
        return if (user != null) ApiResult.Success(user) else ApiResult.Error(ApiError.Unauthorized())
    }

    override fun isAuthenticated(): Boolean = _authState.value == AuthState.AUTHENTICATED
}
