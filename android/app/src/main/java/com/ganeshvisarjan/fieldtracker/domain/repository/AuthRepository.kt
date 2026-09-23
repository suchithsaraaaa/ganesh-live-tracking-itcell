package com.ganeshvisarjan.fieldtracker.domain.repository

import com.ganeshvisarjan.fieldtracker.core.network.ApiResult
import com.ganeshvisarjan.fieldtracker.domain.model.User
import kotlinx.coroutines.flow.StateFlow

enum class AuthState { UNAUTHENTICATED, AUTHENTICATED, LOADING }

/**
 * Field-user accounts are created on the web app by the Main Officer (spec
 * "Field Officer / Ground User Workflow" section 1) — this repository only ever
 * authenticates an existing account. There is no sign-up here by design.
 */
interface AuthRepository {
    val authState: StateFlow<AuthState>
    val currentUser: StateFlow<User?>

    suspend fun login(username: String, password: String): ApiResult<User>
    suspend fun logout()
    suspend fun refreshCurrentUser(): ApiResult<User>
    fun isAuthenticated(): Boolean
}
