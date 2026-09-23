package com.ganeshvisarjan.fieldtracker.feature.splash

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import com.ganeshvisarjan.fieldtracker.R
import com.ganeshvisarjan.fieldtracker.domain.repository.AuthState
import com.ganeshvisarjan.fieldtracker.ui.theme.Accent
import com.ganeshvisarjan.fieldtracker.ui.theme.Base
import com.ganeshvisarjan.fieldtracker.ui.theme.TextPrimary
import com.ganeshvisarjan.fieldtracker.ui.theme.TextSecondary
import com.ganeshvisarjan.fieldtracker.ui.theme.TextTertiary

@Composable
fun SplashScreen(
    onAuthenticated: () -> Unit,
    onUnauthenticated: () -> Unit,
    viewModel: SplashViewModel = hiltViewModel(),
) {
    val resolved by viewModel.resolvedState.collectAsState()

    LaunchedEffect(resolved) {
        when (resolved) {
            AuthState.AUTHENTICATED -> onAuthenticated()
            AuthState.UNAUTHENTICATED -> onUnauthenticated()
            else -> Unit
        }
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Base),
        contentAlignment = Alignment.Center,
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
            modifier = Modifier.padding(horizontal = 32.dp),
        ) {
            Image(
                painter = painterResource(id = R.drawable.ic_police_badge),
                contentDescription = "Telangana State Police Emblem",
                modifier = Modifier.size(130.dp),
            )

            Spacer(Modifier.height(24.dp))

            Text(
                text = "HYDERABAD CITY POLICE",
                style = MaterialTheme.typography.labelMedium,
                letterSpacing = 2.5.sp,
                color = Accent,
                fontWeight = FontWeight.Bold,
            )

            Spacer(Modifier.height(8.dp))

            Text(
                text = "GANESH VISARJAN",
                style = MaterialTheme.typography.headlineMedium.copy(
                    fontWeight = FontWeight.ExtraBold,
                    letterSpacing = 1.sp,
                ),
                color = TextPrimary,
                textAlign = TextAlign.Center,
            )

            Text(
                text = "MONITORING SYSTEM",
                style = MaterialTheme.typography.titleSmall.copy(
                    letterSpacing = 2.sp,
                    fontWeight = FontWeight.SemiBold,
                ),
                color = TextSecondary,
                textAlign = TextAlign.Center,
            )

            Spacer(Modifier.height(12.dp))

            Text(
                text = "A SAFER, UNITED HYDERABAD",
                style = MaterialTheme.typography.labelSmall.copy(
                    letterSpacing = 1.5.sp,
                ),
                color = TextTertiary,
            )
        }

        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .padding(bottom = 48.dp),
        ) {
            LinearProgressIndicator(
                modifier = Modifier
                    .width(180.dp)
                    .height(3.dp),
                color = Accent,
                trackColor = Color(0x33F97316),
            )

            Spacer(Modifier.height(16.dp))

            Text(
                text = "Securing a Safer Tomorrow…",
                style = MaterialTheme.typography.bodySmall,
                color = TextTertiary,
            )
        }
    }
}
