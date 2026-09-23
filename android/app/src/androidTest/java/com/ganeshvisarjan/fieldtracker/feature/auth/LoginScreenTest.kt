package com.ganeshvisarjan.fieldtracker.feature.auth

import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.ganeshvisarjan.fieldtracker.core.network.ApiError
import com.ganeshvisarjan.fieldtracker.core.network.ApiResult
import com.ganeshvisarjan.fieldtracker.domain.model.Role
import com.ganeshvisarjan.fieldtracker.domain.model.User
import com.ganeshvisarjan.fieldtracker.domain.repository.AuthRepository
import com.ganeshvisarjan.fieldtracker.domain.repository.AuthState
import io.mockk.coEvery
import io.mockk.every
import io.mockk.mockk
import kotlinx.coroutines.flow.MutableStateFlow
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Tests actual user-visible behavior (error text shown / navigation callback
 * fired), not just static text presence. [LoginViewModel] is constructed
 * directly with a faked [AuthRepository] and passed straight into
 * [LoginScreen]'s `viewModel` parameter — bypassing `hiltViewModel()`, so no
 * Hilt test runner is required.
 */
@RunWith(AndroidJUnit4::class)
class LoginScreenTest {

    @get:Rule
    val composeRule = createComposeRule()

    private fun viewModelWith(authRepository: AuthRepository) = LoginViewModel(authRepository)

    @Test
    fun invalidLogin_showsBackendErrorMessage_andDoesNotNavigate() {
        val authRepository: AuthRepository = mockk {
            coEvery { login(any(), any()) } returns ApiResult.Error(ApiError.Unauthorized("Invalid credentials."))
        }
        var navigatedToHome = false

        composeRule.setContent {
            LoginScreen(onLoginSuccess = { navigatedToHome = true }, viewModel = viewModelWith(authRepository))
        }

        composeRule.onNodeWithText("Username").performTextInput("pc.constable")
        composeRule.onNodeWithText("Password").performTextInput("wrong-password")
        composeRule.onNodeWithText("LOG IN").performClick()

        composeRule.onNodeWithText("Invalid credentials.").assertExists()
        assert(!navigatedToHome) { "onLoginSuccess must not fire when the backend rejects the login" }
    }

    @Test
    fun successfulLogin_firesOnLoginSuccess() {
        val user = User(
            id = 1, username = "pc.constable", displayName = "PC Constable",
            role = Role.CONSTABLE, policeStation = "Charminar", zone = "Zone 4", division = "South",
        )
        val authRepository: AuthRepository = mockk {
            coEvery { login(any(), any()) } returns ApiResult.Success(user)
            every { authState } returns MutableStateFlow(AuthState.AUTHENTICATED)
            every { currentUser } returns MutableStateFlow(user)
        }
        var navigatedToHome = false

        composeRule.setContent {
            LoginScreen(onLoginSuccess = { navigatedToHome = true }, viewModel = viewModelWith(authRepository))
        }

        composeRule.onNodeWithText("Username").performTextInput("pc.constable")
        composeRule.onNodeWithText("Password").performTextInput("correct-password")
        composeRule.onNodeWithText("LOG IN").performClick()
        composeRule.waitForIdle()

        assert(navigatedToHome) { "onLoginSuccess must fire once the backend confirms login" }
    }

    @Test
    fun blankFields_showsValidationError_withoutCallingTheBackend() {
        val authRepository: AuthRepository = mockk()

        composeRule.setContent {
            LoginScreen(onLoginSuccess = {}, viewModel = viewModelWith(authRepository))
        }

        composeRule.onNodeWithText("LOG IN").performClick()

        composeRule.onNodeWithText("Enter your username and password.").assertExists()
    }
}
