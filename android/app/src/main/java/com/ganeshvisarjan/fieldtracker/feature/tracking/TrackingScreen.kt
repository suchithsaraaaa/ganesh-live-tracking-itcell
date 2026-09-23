package com.ganeshvisarjan.fieldtracker.feature.tracking

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
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
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.CloudDone
import androidx.compose.material.icons.filled.CloudOff
import androidx.compose.material.icons.filled.GpsFixed
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material.icons.filled.Shield
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import com.ganeshvisarjan.fieldtracker.core.network.NetworkState
import com.ganeshvisarjan.fieldtracker.domain.model.HeightClass
import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionEventType
import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionState
import com.ganeshvisarjan.fieldtracker.domain.usecase.ProcessionStateMachine
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
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

internal fun actionLabel(type: ProcessionEventType): String = when (type) {
    ProcessionEventType.REACHED_SITE -> "REACHED SITE"
    ProcessionEventType.PROCESSION_STARTED -> "START PROCESSION"
    ProcessionEventType.REACHED_VISARJAN_SITE -> "REACHED VISARJAN SITE"
    ProcessionEventType.VISARJAN_DONE -> "VISARJAN DONE"
    ProcessionEventType.VISARJAN_NOT_DONE -> "VISARJAN NOT DONE"
    ProcessionEventType.SENT_TO_HOLDING -> "SEND TO HOLDING"
    ProcessionEventType.RETURNED_TO_ORIGIN -> "RETURN TO ORIGIN"
}

@Composable
fun TrackingScreen(
    viewModel: TrackingViewModel = hiltViewModel(),
    onNavigateHome: (() -> Unit)? = null,
) {
    val state by viewModel.uiState.collectAsState()
    var showStopConfirmationDialog by remember { mutableStateOf(false) }
    var pendingConfirmationAction by remember { mutableStateOf<ProcessionEventType?>(null) }

    LaunchedEffect(state.session?.localSessionId) {
        val session = state.session ?: return@LaunchedEffect
        viewModel.ensureServiceStarted(session.localSessionId, session.gpid)
    }

    // Remote Termination Dialog (Admin Force-End)
    if (state.isRemotelyTerminated) {
        AlertDialog(
            onDismissRequest = {
                viewModel.acknowledgeRemoteTermination()
                onNavigateHome?.invoke()
            },
            icon = {
                Icon(
                    imageVector = Icons.Default.Warning,
                    contentDescription = null,
                    tint = StatusRed,
                    modifier = Modifier.size(32.dp),
                )
            },
            title = {
                Text(
                    text = "TRACKING ENDED",
                    style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Bold),
                    color = TextPrimary,
                )
            },
            text = {
                Text(
                    text = "Tracking was ended by an administrator.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = TextSecondary,
                )
            },
            confirmButton = {
                Button(
                    onClick = {
                        viewModel.acknowledgeRemoteTermination()
                        onNavigateHome?.invoke()
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = StatusRed, contentColor = Color.White),
                ) {
                    Text("OK", fontWeight = FontWeight.Bold)
                }
            },
            containerColor = Elevated,
        )
    }

    // Stop Tracking Dialog
    if (showStopConfirmationDialog) {
        AlertDialog(
            onDismissRequest = { showStopConfirmationDialog = false },
            icon = {
                Icon(
                    imageVector = Icons.Default.Warning,
                    contentDescription = null,
                    tint = StatusRed,
                    modifier = Modifier.size(32.dp),
                )
            },
            title = {
                Text(
                    text = "Stop Procession Tracking?",
                    style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Bold),
                    color = TextPrimary,
                )
            },
            text = {
                Text(
                    text = "Are you sure you want to stop tracking for GPID ${state.session?.gpid ?: ""}? This will end the active GPS foreground service and synchronize all final telemetry to the command center.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = TextSecondary,
                )
            },
            confirmButton = {
                Button(
                    onClick = {
                        showStopConfirmationDialog = false
                        viewModel.stopTracking()
                        onNavigateHome?.invoke()
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = StatusRed, contentColor = Color.White),
                ) {
                    Text("YES, STOP TRACKING", fontWeight = FontWeight.Bold)
                }
            },
            dismissButton = {
                TextButton(onClick = { showStopConfirmationDialog = false }) {
                    Text("CANCEL", color = TextSecondary)
                }
            },
            containerColor = Elevated,
        )
    }

    // Lifecycle Action Confirmation Dialog
    pendingConfirmationAction?.let { action ->
        val (title, message) = when (action) {
            ProcessionEventType.VISARJAN_DONE ->
                "Confirm Visarjan Completion" to "Confirm that the idol immersion (Visarjan) is completed for GPID ${state.session?.gpid ?: ""}?"
            ProcessionEventType.VISARJAN_NOT_DONE ->
                "Confirm Visarjan Not Done" to "Record that immersion could not be completed at this time for GPID ${state.session?.gpid ?: ""}?"
            else ->
                "Confirm Action" to "Proceed with ${actionLabel(action)}?"
        }

        AlertDialog(
            onDismissRequest = { pendingConfirmationAction = null },
            icon = {
                Icon(
                    imageVector = if (action == ProcessionEventType.VISARJAN_DONE) Icons.Default.CheckCircle else Icons.Default.Warning,
                    contentDescription = null,
                    tint = if (action == ProcessionEventType.VISARJAN_DONE) StatusGreen else StatusYellow,
                    modifier = Modifier.size(32.dp),
                )
            },
            title = {
                Text(
                    text = title,
                    style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Bold),
                    color = TextPrimary,
                )
            },
            text = {
                Text(
                    text = message,
                    style = MaterialTheme.typography.bodyMedium,
                    color = TextSecondary,
                )
            },
            confirmButton = {
                Button(
                    onClick = {
                        pendingConfirmationAction = null
                        viewModel.submitAction(action)
                    },
                    colors = ButtonDefaults.buttonColors(
                        containerColor = if (action == ProcessionEventType.VISARJAN_DONE) StatusGreen else Accent,
                        contentColor = Base,
                    ),
                ) {
                    Text("CONFIRM", fontWeight = FontWeight.Bold)
                }
            },
            dismissButton = {
                TextButton(onClick = { pendingConfirmationAction = null }) {
                    Text("CANCEL", color = TextSecondary)
                }
            },
            containerColor = Elevated,
        )
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
            // Header identity bar
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column {
                    Text(
                        text = "TELANGANA POLICE • LIVE TRACKER",
                        style = MaterialTheme.typography.labelSmall.copy(
                            letterSpacing = 1.2.sp,
                            fontWeight = FontWeight.SemiBold,
                        ),
                        color = TextSecondary,
                    )
                    Spacer(Modifier.height(2.dp))
                    Text(
                        text = state.session?.gpid ?: state.assignment?.idol?.gpid ?: "—",
                        style = MaterialTheme.typography.headlineMedium.copy(fontWeight = FontWeight.Bold),
                        fontFamily = FontFamily.Monospace,
                        color = TextPrimary,
                    )
                }

                // Live status pill badge
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier
                        .background(
                            color = if (state.serviceRunning) StatusGreen.copy(alpha = 0.15f) else StatusYellow.copy(alpha = 0.15f),
                            shape = RoundedCornerShape(20.dp),
                        )
                        .padding(horizontal = 12.dp, vertical = 6.dp),
                ) {
                    Box(
                        modifier = Modifier
                            .size(8.dp)
                            .background(
                                color = if (state.serviceRunning) StatusGreen else StatusYellow,
                                shape = CircleShape,
                            )
                    )
                    Spacer(Modifier.width(6.dp))
                    Text(
                        text = if (state.serviceRunning) "LIVE" else "INITIALIZING",
                        style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                        color = if (state.serviceRunning) StatusGreen else StatusYellow,
                    )
                }
            }

            Spacer(Modifier.height(16.dp))

            // Idol & Jurisdiction Operational Card
            val idol = state.assignment?.idol
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = Elevated),
                shape = RoundedCornerShape(14.dp),
            ) {
                Column(Modifier.padding(16.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text(
                            text = idol?.ownerName ?: idol?.associationName ?: "Ganesh Idol",
                            style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                            color = TextPrimary,
                            modifier = Modifier.weight(1f),
                        )

                        // Height badge
                        val heightFeet = idol?.heightFeet
                        if (heightFeet != null) {
                            val badgeColor = when (idol.heightClass) {
                                HeightClass.RED -> StatusRed
                                HeightClass.YELLOW -> StatusYellow
                                HeightClass.GREEN -> StatusGreen
                                else -> Accent
                            }
                            Box(
                                modifier = Modifier
                                    .background(badgeColor.copy(alpha = 0.2f), RoundedCornerShape(6.dp))
                                    .padding(horizontal = 8.dp, vertical = 4.dp),
                            ) {
                                Text(
                                    text = "${"%.1f".format(heightFeet)} ft",
                                    style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                                    color = badgeColor,
                                )
                            }
                        }
                    }

                    Spacer(Modifier.height(6.dp))

                    val ps = idol?.policeStation ?: "Station Assigned"
                    val zone = idol?.originZone ?: idol?.currentZone ?: "Zone"
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(
                            imageVector = Icons.Default.Shield,
                            contentDescription = null,
                            tint = TextSecondary,
                            modifier = Modifier.size(14.dp),
                        )
                        Spacer(Modifier.width(6.dp))
                        Text(
                            text = "$ps • $zone",
                            style = MaterialTheme.typography.bodySmall,
                            color = TextSecondary,
                        )
                    }
                }
            }

            Spacer(Modifier.height(14.dp))

            // Current State Header Card
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = Elevated),
                shape = RoundedCornerShape(14.dp),
            ) {
                Column(Modifier.padding(16.dp)) {
                    Text(
                        text = "CURRENT PROCESSION STAGE",
                        style = MaterialTheme.typography.labelSmall.copy(letterSpacing = 1.sp, fontWeight = FontWeight.Bold),
                        color = TextSecondary,
                    )
                    Spacer(Modifier.height(6.dp))
                    Text(
                        text = state.processionState?.name?.replace('_', ' ') ?: "PROCESSION STARTED",
                        style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Bold),
                        color = Accent,
                        modifier = Modifier.testTag("procession_state_header"),
                    )
                }
            }

            Spacer(Modifier.height(14.dp))

            // Real-time GPS Telemetry & Sync Card
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = Elevated),
                shape = RoundedCornerShape(16.dp),
            ) {
                Column(Modifier.padding(18.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Icon(
                            imageVector = Icons.Default.GpsFixed,
                            contentDescription = null,
                            tint = Accent,
                            modifier = Modifier.size(18.dp),
                        )
                        Spacer(Modifier.width(8.dp))
                        Text(
                            "FIELD GPS TELEMETRY",
                            style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold, letterSpacing = 1.sp),
                            color = Accent,
                        )
                    }

                    Spacer(Modifier.height(12.dp))

                    val fix = state.lastFix
                    if (fix != null) {
                        Text(
                            text = "${"%.6f".format(fix.latitude)}, ${"%.6f".format(fix.longitude)}",
                            style = MaterialTheme.typography.titleLarge.copy(
                                fontWeight = FontWeight.Bold,
                                fontFamily = FontFamily.Monospace,
                            ),
                            color = TextPrimary,
                        )
                        Spacer(Modifier.height(4.dp))
                        val accuracy = fix.accuracyMeters
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(
                                text = if (accuracy != null) "Accuracy: ±${accuracy.toInt()}m" else "Accuracy: Available",
                                style = MaterialTheme.typography.bodySmall,
                                color = if (accuracy != null && accuracy <= 30f) StatusGreen else StatusYellow,
                            )
                            val timeStr = SimpleDateFormat("hh:mm:ss a", Locale.getDefault()).format(Date(fix.timestampMillis))
                            Spacer(Modifier.width(12.dp))
                            Text(
                                text = "Fix: $timeStr",
                                style = MaterialTheme.typography.bodySmall,
                                color = TextTertiary,
                            )
                        }
                    } else {
                        Text(
                            text = "Acquiring satellite lock…",
                            style = MaterialTheme.typography.bodyLarge,
                            color = TextSecondary,
                        )
                    }

                    Spacer(Modifier.height(14.dp))

                    // Network & Sync status row
                    val isOnline = state.networkState == NetworkState.ONLINE
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .background(Elevated2, RoundedCornerShape(8.dp))
                            .padding(10.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween,
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                imageVector = if (isOnline) Icons.Default.CloudDone else Icons.Default.CloudOff,
                                contentDescription = null,
                                tint = if (isOnline) StatusGreen else StatusYellow,
                                modifier = Modifier.size(18.dp),
                            )
                            Spacer(Modifier.width(8.dp))
                            Text(
                                text = if (isOnline) "Connected to Command Center" else "Offline — Recording GPS Locally",
                                style = MaterialTheme.typography.bodySmall.copy(fontWeight = FontWeight.Medium),
                                color = TextPrimary,
                            )
                        }

                        if (state.pendingTelemetryCount > 0) {
                            Text(
                                text = "${state.pendingTelemetryCount} queued",
                                style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                                color = StatusYellow,
                            )
                        } else {
                            Text(
                                text = "Synced",
                                style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                                color = StatusGreen,
                            )
                        }
                    }
                }
            }

            Spacer(Modifier.height(16.dp))

            // Action Error Message
            state.actionError?.let { error ->
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = Color(0x33EF4444)),
                    shape = RoundedCornerShape(10.dp),
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(12.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween,
                    ) {
                        Text(
                            text = error,
                            style = MaterialTheme.typography.bodySmall,
                            color = StatusRed,
                            modifier = Modifier.weight(1f),
                        )
                        TextButton(onClick = viewModel::clearActionError) {
                            Text("DISMISS", color = TextPrimary, style = MaterialTheme.typography.labelSmall)
                        }
                    }
                }
                Spacer(Modifier.height(14.dp))
            }

            // Operational Action Buttons
            val available = state.availableActions
            if (available.isNotEmpty()) {
                Text(
                    text = "OPERATIONAL ACTIONS",
                    style = MaterialTheme.typography.labelMedium.copy(letterSpacing = 1.sp, fontWeight = FontWeight.Bold),
                    color = TextSecondary,
                )
                Spacer(Modifier.height(8.dp))

                available.forEach { action ->
                    val isDangerous = action == ProcessionEventType.VISARJAN_DONE || action == ProcessionEventType.VISARJAN_NOT_DONE
                    val buttonColor = when (action) {
                        ProcessionEventType.VISARJAN_DONE -> StatusGreen
                        ProcessionEventType.VISARJAN_NOT_DONE -> StatusYellow
                        else -> Accent
                    }

                    Button(
                        onClick = {
                            if (isDangerous) {
                                pendingConfirmationAction = action
                            } else {
                                viewModel.submitAction(action)
                            }
                        },
                        enabled = !state.isSubmittingAction,
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(54.dp)
                            .padding(bottom = 8.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = buttonColor,
                            contentColor = Base,
                        ),
                        shape = RoundedCornerShape(12.dp),
                    ) {
                        if (state.isSubmittingAction) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(20.dp),
                                strokeWidth = 2.dp,
                                color = Base,
                            )
                            Spacer(Modifier.width(8.dp))
                            Text("Recording…", fontWeight = FontWeight.Bold)
                        } else {
                            Text(
                                actionLabel(action),
                                style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold),
                            )
                        }
                    }
                }
            } else if (state.processionState?.let { ProcessionStateMachine.isTerminal(it) } == true) {
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
                                modifier = Modifier.size(22.dp),
                            )
                            Spacer(Modifier.width(8.dp))
                            Text(
                                text = "PROCESSION CONCLUDED",
                                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                                color = StatusGreen,
                            )
                        }
                        Spacer(Modifier.height(4.dp))
                        Text(
                            text = "This procession has reached its conclusion. All telemetry and lifecycle events are safely recorded.",
                            style = MaterialTheme.typography.bodySmall,
                            color = TextSecondary,
                        )
                    }
                }
            }

            Spacer(Modifier.height(20.dp))

            // STOP TRACKING Button (with confirmation)
            OutlinedButton(
                onClick = { showStopConfirmationDialog = true },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(50.dp),
                colors = ButtonDefaults.outlinedButtonColors(contentColor = StatusRed),
                shape = RoundedCornerShape(10.dp),
            ) {
                Icon(
                    imageVector = Icons.Default.Stop,
                    contentDescription = null,
                    tint = StatusRed,
                    modifier = Modifier.size(18.dp),
                )
                Spacer(Modifier.width(8.dp))
                Text(
                    "STOP TRACKING",
                    color = StatusRed,
                    style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold),
                )
            }

            Spacer(Modifier.height(24.dp))

            // Timeline Card
            Text(
                "PROCESSION TIMELINE",
                style = MaterialTheme.typography.labelMedium.copy(letterSpacing = 1.sp, fontWeight = FontWeight.Bold),
                color = TextSecondary,
            )
            Spacer(Modifier.height(8.dp))
            Timeline(state.processionState)
        }
    }
}

@Composable
private fun Timeline(currentState: ProcessionState?) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = Elevated),
        shape = RoundedCornerShape(12.dp),
    ) {
        Column(Modifier.padding(16.dp)) {
            val stages = ProcessionStateMachine.timelineOrder
            stages.forEach { state ->
                val isCurrent = state == currentState
                val isPast = currentState != null && stages.indexOf(state) < stages.indexOf(currentState)
                val color = when {
                    isCurrent -> Accent
                    isPast -> StatusGreen
                    else -> TextTertiary
                }
                Row(
                    modifier = Modifier.padding(vertical = 5.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Box(
                        modifier = Modifier
                            .size(10.dp)
                            .background(color, CircleShape)
                    )
                    Spacer(Modifier.width(12.dp))
                    Text(
                        text = state.name.replace('_', ' '),
                        color = if (isCurrent) TextPrimary else color,
                        style = if (isCurrent) MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold) else MaterialTheme.typography.bodySmall,
                    )
                }
            }
        }
    }
}
