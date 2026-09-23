package com.ganeshvisarjan.fieldtracker

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Modifier
import androidx.navigation.compose.rememberNavController
import com.ganeshvisarjan.fieldtracker.core.auth.SessionExpiredNotifier
import com.ganeshvisarjan.fieldtracker.domain.repository.AuthRepository
import com.ganeshvisarjan.fieldtracker.navigation.AppNavGraph
import com.ganeshvisarjan.fieldtracker.navigation.Destinations
import com.ganeshvisarjan.fieldtracker.ui.theme.VisarjanTrackingTheme
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.launch
import javax.inject.Inject

@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    @Inject lateinit var sessionExpiredNotifier: SessionExpiredNotifier
    @Inject lateinit var authRepository: AuthRepository

    override fun onCreate(savedInstanceState: Bundle?) {
        // Must be called before super.onCreate() — see themes.xml
        // Theme.VisarjanTracking.Starting for the matching splash theme.
        installSplashScreen()
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            VisarjanTrackingTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    val navController = rememberNavController()
                    AppNavGraph(navController = navController)

                    // Centralized 401 handling (spec section 34): any request across the
                    // app can trigger this, so the reaction lives once, at the root.
                    LaunchedEffect(Unit) {
                        sessionExpiredNotifier.events.collect {
                            launch { authRepository.logout() }
                            navController.navigate(Destinations.LOGIN) {
                                popUpTo(0) { inclusive = true }
                            }
                        }
                    }
                }
            }
        }
    }
}
