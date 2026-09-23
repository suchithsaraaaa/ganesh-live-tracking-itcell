package com.ganeshvisarjan.fieldtracker.navigation

import androidx.compose.runtime.Composable
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.ganeshvisarjan.fieldtracker.core.config.AppConfig
import com.ganeshvisarjan.fieldtracker.feature.assignment.AssignmentScreen
import com.ganeshvisarjan.fieldtracker.feature.auth.LoginScreen
import com.ganeshvisarjan.fieldtracker.feature.debug.DebugScreen
import com.ganeshvisarjan.fieldtracker.feature.home.HomeScreen
import com.ganeshvisarjan.fieldtracker.feature.profile.ProfileScreen
import com.ganeshvisarjan.fieldtracker.feature.splash.SplashScreen
import com.ganeshvisarjan.fieldtracker.feature.tracking.TrackingScreen

@Composable
fun AppNavGraph(navController: NavHostController = rememberNavController()) {
    NavHost(navController = navController, startDestination = Destinations.SPLASH) {

        composable(Destinations.SPLASH) {
            SplashScreen(
                onAuthenticated = {
                    navController.navigate(Destinations.HOME) {
                        popUpTo(Destinations.SPLASH) { inclusive = true }
                    }
                },
                onUnauthenticated = {
                    navController.navigate(Destinations.LOGIN) {
                        popUpTo(Destinations.SPLASH) { inclusive = true }
                    }
                },
            )
        }

        composable(Destinations.LOGIN) {
            LoginScreen(
                onLoginSuccess = {
                    navController.navigate(Destinations.HOME) {
                        popUpTo(Destinations.LOGIN) { inclusive = true }
                    }
                },
            )
        }

        composable(Destinations.HOME) {
            HomeScreen(
                onOpenAssignment = { navController.navigate(Destinations.ASSIGNMENT) },
                onOpenActiveTracking = { navController.navigate(Destinations.TRACKING) },
                onOpenProfile = { navController.navigate(Destinations.PROFILE) },
            )
        }

        composable(Destinations.ASSIGNMENT) {
            AssignmentScreen(
                onProcessionStarted = {
                    navController.navigate(Destinations.TRACKING) {
                        popUpTo(Destinations.HOME)
                    }
                },
            )
        }

        composable(Destinations.TRACKING) {
            TrackingScreen()
        }

        composable(Destinations.PROFILE) {
            ProfileScreen(
                onLoggedOut = {
                    navController.navigate(Destinations.LOGIN) {
                        popUpTo(0) { inclusive = true }
                    }
                },
            )
        }

        if (AppConfig.debugScreenEnabled) {
            composable(Destinations.DEBUG) { DebugScreen() }
        }
    }
}
