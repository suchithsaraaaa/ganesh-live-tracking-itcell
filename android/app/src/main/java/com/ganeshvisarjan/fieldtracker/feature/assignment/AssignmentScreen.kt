package com.ganeshvisarjan.fieldtracker.feature.assignment

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.Settings
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Assignment
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.GpsFixed
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.app.ActivityCompat
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import com.ganeshvisarjan.fieldtracker.domain.usecase.ValidateProcessionStartUseCase.Result as Readiness
import com.ganeshvisarjan.fieldtracker.location.LocationPermissions
import com.ganeshvisarjan.fieldtracker.location.NextSetupAction
import com.ganeshvisarjan.fieldtracker.ui.theme.Accent
import com.ganeshvisarjan.fieldtracker.ui.theme.Base
import com.ganeshvisarjan.fieldtracker.ui.theme.Elevated
import com.ganeshvisarjan.fieldtracker.ui.theme.Elevated2
import com.ganeshvisarjan.fieldtracker.ui.theme.StatusGreen
import com.ganeshvisarjan.fieldtracker.ui.theme.StatusRed
import com.ganeshvisarjan.fieldtracker.ui.theme.StatusYellow
import com.ganeshvisarjan.fieldtracker.ui.theme.TextPrimary
import com.ganeshvisarjan.fieldtracker.ui.theme.TextSecondary
import com.ganeshvisarjan.fieldtracker.ui.theme.TextTertiary

@Composable
fun AssignmentScreen(
    onProcessionStarted: (sessionLocalId: String) -> Unit,
    viewModel: AssignmentViewModel = hiltViewModel(),
) {
    val state by viewModel.uiState.collectAsState()
    val context = LocalContext.current
    val activity = context as? Activity
    val lifecycleOwner = LocalLifecycleOwner.current

    // Activity Result Launchers for runtime permissions
    val foregroundPermissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestMultiplePermissions()
    ) { perms ->
        val fine = perms[Manifest.permission.ACCESS_FINE_LOCATION] ?: false
        val coarse = perms[Manifest.permission.ACCESS_COARSE_LOCATION] ?: false
        val anyGranted = fine || coarse
        val permanentlyDenied = !anyGranted && activity != null &&
            !ActivityCompat.shouldShowRequestPermissionRationale(activity, Manifest.permission.ACCESS_FINE_LOCATION)
        viewModel.refreshPermissionState(isPermanentlyDenied = permanentlyDenied)
    }

    val notificationPermissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission()
    ) { _ ->
        viewModel.refreshPermissionState()
    }

    // Auto-refresh permission and hardware state when returning from system Settings
    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                viewModel.refreshPermissionState()
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose {
            lifecycleOwner.lifecycle.removeObserver(observer)
        }
    }

    LaunchedEffect(state.startedSessionLocalId) {
        state.startedSessionLocalId?.let(onProcessionStarted)
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Base),
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(20.dp),
        ) {
            Text(
                text = "DUTY ASSIGNMENT",
                style = MaterialTheme.typography.labelMedium.copy(
                    letterSpacing = 1.5.sp,
                    fontWeight = FontWeight.Bold,
                ),
                color = Accent,
            )

            Spacer(Modifier.height(4.dp))

            Text(
                text = "Ganesh Idol Procession",
                style = MaterialTheme.typography.headlineSmall.copy(fontWeight = FontWeight.Bold),
                color = TextPrimary,
            )

            Spacer(Modifier.height(16.dp))

            when {
                state.isLoading && state.assignment == null -> {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(260.dp),
                        contentAlignment = Alignment.Center,
                    ) {
                        CircularProgressIndicator(color = Accent)
                    }
                }

                state.assignment == null -> {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = Elevated),
                        shape = RoundedCornerShape(16.dp),
                    ) {
                        Column(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(28.dp),
                            horizontalAlignment = Alignment.CenterHorizontally,
                        ) {
                            Icon(
                                imageVector = Icons.Default.Assignment,
                                contentDescription = null,
                                tint = TextTertiary,
                                modifier = Modifier.size(54.dp),
                            )

                            Spacer(Modifier.height(16.dp))

                            Text(
                                text = "No Active GPID Assigned",
                                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                                color = TextPrimary,
                            )

                            Spacer(Modifier.height(8.dp))

                            Text(
                                text = "You currently do not have an active idol assignment. Please contact your Station Officer (SHO) or Control Room to assign your duty GPID.",
                                style = MaterialTheme.typography.bodyMedium,
                                color = TextSecondary,
                                textAlign = TextAlign.Center,
                            )

                            Spacer(Modifier.height(24.dp))

                            Button(
                                onClick = viewModel::loadAssignment,
                                colors = ButtonDefaults.buttonColors(
                                    containerColor = Elevated2,
                                    contentColor = TextPrimary,
                                ),
                                shape = RoundedCornerShape(10.dp),
                            ) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Icon(
                                        imageVector = Icons.Default.Refresh,
                                        contentDescription = null,
                                        modifier = Modifier.size(18.dp),
                                    )
                                    Spacer(Modifier.width(8.dp))
                                    Text("CHECK AGAIN")
                                }
                            }
                        }
                    }
                }

                else -> {
                    AssignmentCard(assignment = state.assignment!!, onClick = {})

                    Spacer(Modifier.height(16.dp))

                    // Location Setup Card (State-aware, dynamic OS reflection)
                    val setup = state.setupStatus
                    val nextAction = setup.nextRequiredAction

                    val triggerAction: () -> Unit = {
                        when (nextAction) {
                            NextSetupAction.REQUEST_FOREGROUND_PERMISSION,
                            NextSetupAction.REQUEST_PRECISE_PERMISSION -> {
                                foregroundPermissionLauncher.launch(LocationPermissions.foregroundPermissions)
                            }
                            NextSetupAction.ENABLE_LOCATION_SERVICES -> {
                                context.startActivity(Intent(Settings.ACTION_LOCATION_SOURCE_SETTINGS))
                            }
                            NextSetupAction.REQUEST_NOTIFICATION_PERMISSION -> {
                                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                                    notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
                                }
                            }
                            NextSetupAction.OPTIMIZE_BATTERY -> {
                                try {
                                    val intent = Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS)
                                    context.startActivity(intent)
                                } catch (_: Exception) {
                                    val intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                                        data = Uri.fromParts("package", context.packageName, null)
                                    }
                                    context.startActivity(intent)
                                }
                            }
                            NextSetupAction.OPEN_APP_SETTINGS -> {
                                val intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                                    data = Uri.fromParts("package", context.packageName, null)
                                }
                                context.startActivity(intent)
                            }
                            NextSetupAction.NONE -> viewModel.refreshPermissionState()
                        }
                    }

                    if (setup.isFullyReady) {
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            colors = CardDefaults.cardColors(containerColor = Color(0x1F22C55E)),
                            shape = RoundedCornerShape(12.dp),
                        ) {
                            Column(Modifier.padding(16.dp)) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Icon(
                                        imageVector = Icons.Default.CheckCircle,
                                        contentDescription = null,
                                        tint = StatusGreen,
                                        modifier = Modifier.size(20.dp),
                                    )
                                    Spacer(Modifier.width(8.dp))
                                    Text(
                                        "LOCATION READY",
                                        style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold),
                                        color = StatusGreen,
                                    )
                                }
                                Spacer(Modifier.height(4.dp))
                                Text(
                                    "Precise GPS, location services, and persistent alerts are active for continuous tracking.",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = TextSecondary,
                                )
                            }
                        }
                    } else {
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            colors = CardDefaults.cardColors(containerColor = Elevated),
                            shape = RoundedCornerShape(12.dp),
                        ) {
                            Column(Modifier.padding(16.dp)) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Icon(
                                        imageVector = Icons.Default.Warning,
                                        contentDescription = null,
                                        tint = StatusYellow,
                                        modifier = Modifier.size(20.dp),
                                    )
                                    Spacer(Modifier.width(8.dp))
                                    Text(
                                        "LOCATION SETUP REQUIRED",
                                        style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold),
                                        color = TextPrimary,
                                    )
                                }

                                Spacer(Modifier.height(6.dp))

                                Text(
                                    "Continuous tracking requires high-accuracy GPS, location services, and service notifications.",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = TextSecondary,
                                )

                                Spacer(Modifier.height(12.dp))

                                StatusRow(
                                    title = "Precise location",
                                    isSatisfied = setup.hasFineLocation,
                                    detail = when {
                                        setup.hasFineLocation -> "Granted (High Accuracy GPS)"
                                        setup.hasCoarseLocation -> "Approximate only — Precise required"
                                        else -> "Not granted"
                                    },
                                )
                                StatusRow(
                                    title = "Location services",
                                    isSatisfied = setup.isLocationServiceEnabled,
                                    detail = if (setup.isLocationServiceEnabled) "GPS hardware enabled" else "Location Services OFF in settings",
                                )
                                StatusRow(
                                    title = "Tracking notification",
                                    isSatisfied = setup.hasNotificationPermission,
                                    detail = if (setup.hasNotificationPermission) "Persistent alert allowed" else "Required for foreground service",
                                )

                                Spacer(Modifier.height(14.dp))

                                val actionText = when (nextAction) {
                                    NextSetupAction.REQUEST_FOREGROUND_PERMISSION -> "GRANT LOCATION PERMISSION"
                                    NextSetupAction.REQUEST_PRECISE_PERMISSION -> "GRANT PRECISE LOCATION"
                                    NextSetupAction.ENABLE_LOCATION_SERVICES -> "TURN ON LOCATION SERVICES"
                                    NextSetupAction.REQUEST_NOTIFICATION_PERMISSION -> "ENABLE NOTIFICATIONS"
                                    NextSetupAction.OPTIMIZE_BATTERY -> "DISABLE BATTERY OPTIMIZATION"
                                    NextSetupAction.OPEN_APP_SETTINGS -> "OPEN APP SETTINGS"
                                    NextSetupAction.NONE -> "ALL PERMISSIONS READY"
                                }

                                Button(
                                    onClick = triggerAction,
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .height(48.dp),
                                    colors = ButtonDefaults.buttonColors(containerColor = Accent, contentColor = Base),
                                    shape = RoundedCornerShape(8.dp),
                                ) {
                                    Text(actionText, fontWeight = FontWeight.Bold)
                                }

                                Spacer(Modifier.height(8.dp))

                                OutlinedButton(
                                    onClick = triggerAction,
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .height(42.dp),
                                    shape = RoundedCornerShape(8.dp),
                                ) {
                                    Text("CHECK PERMISSIONS AGAIN")
                                }
                            }
                        }
                    }

                    Spacer(Modifier.height(16.dp))

                    // Reached Site Card
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = Elevated),
                        shape = RoundedCornerShape(12.dp),
                    ) {
                        Column(Modifier.padding(16.dp)) {
                            Text(
                                text = "SITE ARRIVAL",
                                style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                                color = TextSecondary,
                            )

                            Spacer(Modifier.height(6.dp))

                            if (state.reachedSiteRecorded) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Icon(
                                        imageVector = Icons.Default.CheckCircle,
                                        contentDescription = null,
                                        tint = StatusGreen,
                                        modifier = Modifier.size(24.dp),
                                    )
                                    Spacer(Modifier.width(10.dp))
                                    Column {
                                        Text(
                                            text = "✓ REACHED SITE",
                                            style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                                            color = StatusGreen,
                                        )
                                        state.reachedSiteTimestamp?.let {
                                            Text(
                                                text = it,
                                                style = MaterialTheme.typography.bodySmall,
                                                color = TextSecondary,
                                            )
                                        }
                                        state.reachedSiteCoordinates?.let {
                                            Text(
                                                text = "GPS: $it",
                                                style = MaterialTheme.typography.bodySmall,
                                                color = TextTertiary,
                                            )
                                        }
                                    }
                                }
                            } else {
                                Text(
                                    text = "Confirm physical presence at the pandal/site before commencing procession tracking.",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = TextSecondary,
                                )

                                Spacer(Modifier.height(12.dp))

                                OutlinedButton(
                                    onClick = viewModel::markReachedSite,
                                    enabled = !state.isRecordingReachedSite,
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .height(48.dp),
                                    shape = RoundedCornerShape(8.dp),
                                ) {
                                    if (state.isRecordingReachedSite) {
                                        CircularProgressIndicator(
                                            modifier = Modifier.size(18.dp),
                                            strokeWidth = 2.dp,
                                            color = Accent,
                                        )
                                        Spacer(Modifier.width(8.dp))
                                        Text("Confirming arrival…")
                                    } else {
                                        Text("I'VE REACHED THE SITE", fontWeight = FontWeight.Bold)
                                    }
                                }

                                state.reachedSiteError?.let {
                                    Spacer(Modifier.height(8.dp))
                                    Text(
                                        text = it,
                                        color = StatusRed,
                                        style = MaterialTheme.typography.bodySmall,
                                    )
                                }
                            }
                        }
                    }

                    Spacer(Modifier.height(16.dp))

                    // Check Location Card
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = Elevated),
                        shape = RoundedCornerShape(12.dp),
                    ) {
                        Column(Modifier.padding(16.dp)) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                verticalAlignment = Alignment.CenterVertically,
                            ) {
                                Icon(
                                    imageVector = Icons.Default.GpsFixed,
                                    contentDescription = null,
                                    tint = Accent,
                                    modifier = Modifier.size(22.dp),
                                )
                                Spacer(Modifier.width(8.dp))
                                Text(
                                    "GPS Signal Readiness",
                                    style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold),
                                    color = TextPrimary,
                                )
                            }

                            Spacer(Modifier.height(10.dp))

                            ReadinessSummary(state.readiness)

                            Spacer(Modifier.height(14.dp))

                            OutlinedButton(
                                onClick = viewModel::checkLocation,
                                enabled = !state.isCheckingLocation,
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .height(48.dp),
                                shape = RoundedCornerShape(8.dp),
                            ) {
                                if (state.isCheckingLocation) {
                                    CircularProgressIndicator(
                                        modifier = Modifier.size(18.dp),
                                        strokeWidth = 2.dp,
                                        color = Accent,
                                    )
                                    Spacer(Modifier.width(8.dp))
                                    Text("Acquiring GPS fix…")
                                } else {
                                    Text("CHECK LOCATION")
                                }
                            }
                        }
                    }

                    Spacer(Modifier.height(24.dp))

                    val ready = state.readiness as? Readiness.Ready
                    Button(
                        onClick = viewModel::startProcession,
                        enabled = ready != null && !state.isStarting,
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(56.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = Accent,
                            contentColor = Base,
                            disabledContainerColor = Elevated2,
                            disabledContentColor = TextTertiary,
                        ),
                        shape = RoundedCornerShape(12.dp),
                    ) {
                        if (state.isStarting) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(20.dp),
                                strokeWidth = 2.5.dp,
                                color = Base,
                            )
                            Spacer(Modifier.width(8.dp))
                            Text("Starting procession…", fontWeight = FontWeight.Bold)
                        } else {
                            Text(
                                "START PROCESSION",
                                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                            )
                        }
                    }

                    state.startError?.let {
                        Spacer(Modifier.height(12.dp))
                        Box(
                            modifier = Modifier
                                .fillMaxWidth()
                                .background(Color(0x22D9524A), RoundedCornerShape(8.dp))
                                .padding(12.dp),
                        ) {
                            Text(
                                text = it,
                                color = StatusRed,
                                style = MaterialTheme.typography.bodySmall,
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun StatusRow(
    title: String,
    isSatisfied: Boolean,
    detail: String,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 3.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(
            imageVector = if (isSatisfied) Icons.Default.CheckCircle else Icons.Default.Close,
            contentDescription = null,
            tint = if (isSatisfied) StatusGreen else StatusRed,
            modifier = Modifier.size(16.dp),
        )
        Spacer(Modifier.width(8.dp))
        Column {
            Text(
                text = title,
                style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Medium),
                color = TextPrimary,
            )
            Text(
                text = detail,
                style = MaterialTheme.typography.bodySmall,
                color = if (isSatisfied) TextSecondary else StatusYellow,
            )
        }
    }
}

@Composable
private fun ReadinessSummary(readiness: Readiness?) {
    when (readiness) {
        null -> Text(
            "Tap Check Location to acquire a fresh GPS fix before starting the procession.",
            color = TextSecondary,
            style = MaterialTheme.typography.bodySmall,
        )
        is Readiness.WaitingForGps -> Text(
            "Getting your current location…",
            color = TextSecondary,
            style = MaterialTheme.typography.bodySmall,
        )
        is Readiness.GpsAccuracyTooLow -> Text(
            "Unable to obtain a precise enough location (±${readiness.accuracyMeters.toInt()}m). Move to open sky and try again.",
            color = StatusYellow,
            style = MaterialTheme.typography.bodySmall,
        )
        is Readiness.PreciseLocationRequired -> Text(
            "Precise GPS location required to start procession.",
            color = StatusRed,
            style = MaterialTheme.typography.bodySmall,
        )
        is Readiness.AssignmentNotActive -> Text(
            "This assignment is not currently active.",
            color = StatusRed,
            style = MaterialTheme.typography.bodySmall,
        )
        is Readiness.AlreadyStarted -> Text(
            "Procession already started for this GPID.",
            color = TextSecondary,
            style = MaterialTheme.typography.bodySmall,
        )
        is Readiness.Ready -> {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    imageVector = Icons.Default.CheckCircle,
                    contentDescription = null,
                    tint = StatusGreen,
                    modifier = Modifier.size(18.dp),
                )
                Spacer(Modifier.width(6.dp))
                Text(
                    "Ready to start — ±${readiness.accuracyMeters.toInt()}m accuracy.",
                    color = StatusGreen,
                    style = MaterialTheme.typography.bodySmall.copy(fontWeight = FontWeight.Medium),
                )
            }
        }
    }
}
