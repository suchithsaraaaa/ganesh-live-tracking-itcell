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
import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionEventType
import com.ganeshvisarjan.fieldtracker.domain.model.ProcessionState
import com.ganeshvisarjan.fieldtracker.domain.usecase.ProcessionStateMachine
import com.ganeshvisarjan.fieldtracker.ui.theme.Accent
import com.ganeshvisarjan.fieldtracker.ui.theme.Base
import com.ganeshvisarjan.fieldtracker.ui.theme.Elevated
import com.ganeshvisarjan.fieldtracker.ui.theme.Elevated2
import com.ganeshvisarjan.fieldtracker.ui.theme.StatusBlue
import com.ganeshvisarjan.fieldtracker.ui.theme.StatusGreen
import com.ganeshvisarjan.fieldtracker.ui.theme.StatusRed
import com.ganeshvisarjan.fieldtracker.ui.theme.StatusYellow
import com.ganeshvisarjan.fieldtracker.ui.theme.TextPrimary
import com.ganeshvisarjan.fieldtracker.ui.theme.TextSecondary
import com.ganeshvisarjan.fieldtracker.ui.theme.TextTertiary

private fun actionLabel(type: ProcessionEventType): String = when (type) {
    ProcessionEventType.PROCESSION_STARTED -> "PROCESSION STARTED"
    ProcessionEventType.MOVING -> "MOVING"
    ProcessionEventType.REACHED_VISARJAN_AREA -> "REACHED VISARJAN AREA"
    ProcessionEventType.VISARJAN_DONE -> "VISARJAN DONE"
    ProcessionEventType.HOLDING -> "PUT IN HOLDING"
    ProcessionEventType.RETURNING_TO_PANDAL -> "RETURNING TO PANDAL"
    ProcessionEventType.RETURNED_TO_PANDAL -> "RETURNED TO PANDAL"
}

@Composable
fun TrackingScreen(
    viewModel: TrackingViewModel = hiltViewModel(),
) {
    val state by viewModel.uiState.collectAsState()
    var showStopConfirmationDialog by remember { mutableStateOf(false) }

    LaunchedEffect(state.session?.localSessionId) {
        val session = state.session ?: return@LaunchedEffect
        viewModel.ensureServiceStarted(session.localSessionId, session.gpid)
    }

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
                    text = "Are you sure you want to stop tracking for GPID ${state.session?.gpid ?: ""}? This will end the active GPS session and synchronize all final telemetry to the command center.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = TextSecondary,
                )
            },
            confirmButton = {
                Button(
                    onClick = {
                        showStopConfirmationDialog = false
                        viewModel.stopTracking()
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
            // Header with LIVE badge
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column {
                    Text("LIVE TRACKING", style = MaterialTheme.typography.labelMedium.copy(letterSpacing = 1.5.sp), color = TextSecondary)
                    Text(
                        state.session?.gpid ?: "—",
                        style = MaterialTheme.typography.headlineMedium.copy(fontWeight = FontWeight.Bold),
                        fontFamily = FontFamily.Monospace,
                        color = TextPrimary,
                    )
                }

                // Live status badge
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

            Spacer(Modifier.height(8.dp))

            Text(
                text = state.processionState?.name?.replace('_', ' ') ?: "—",
                style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Bold),
                color = Accent,
                modifier = Modifier.testTag("procession_state_header"),
            )

            Spacer(Modifier.height(16.dp))

            // Real-time telemetry card
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
                        val accuracy = fix.accuracyMeters
                        if (accuracy != null) {
                            Text(
                                text = "Accuracy: ±${accuracy.toInt()}m",
                                style = MaterialTheme.typography.bodySmall,
                                color = if (accuracy <= 30f) StatusGreen else StatusYellow,
                            )
                        } else {
                            Text(
                                text = "Accuracy: —",
                                style = MaterialTheme.typography.bodySmall,
                                color = StatusYellow,
                            )
                        }
                    } else {
                        Text(
                            text = "Acquiring satellite signal…",
                            style = MaterialTheme.typography.bodyLarge,
                            color = TextSecondary,
                        )
                    }

                    Spacer(Modifier.height(14.dp))

                    // Network & Sync status
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
                                text = if (isOnline) "Connected to EC2" else "Offline — Recording GPS",
                                style = MaterialTheme.typography.bodySmall.copy(fontWeight = FontWeight.Medium),
                                color = TextPrimary,
                            )
                        }

                        if (state.pendingTelemetryCount > 0) {
                            Text(
                                text = "${state.pendingTelemetryCount} queued",
                                style = MaterialTheme.typography.labelSmall,
                                color = StatusYellow,
                            )
                        } else {
                            Text(
                                text = "Synced",
                                style = MaterialTheme.typography.labelSmall,
                                color = StatusGreen,
                            )
                        }
                    }
                }
            }

            Spacer(Modifier.height(20.dp))

            Text("PROCESSION TIMELINE", style = MaterialTheme.typography.labelMedium.copy(letterSpacing = 1.sp), color = TextSecondary)
            Spacer(Modifier.height(8.dp))
            Timeline(state.processionState)

            Spacer(Modifier.height(20.dp))

            // Action buttons
            state.availableActions.forEach { action ->
                Button(
                    onClick = { viewModel.submitAction(action) },
                    enabled = !state.isSubmittingAction,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(52.dp)
                        .padding(bottom = 8.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = Accent,
                        contentColor = Base,
                    ),
                    shape = RoundedCornerShape(10.dp),
                ) {
                    Text(
                        actionLabel(action),
                        style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold),
                    )
                }
            }

            state.actionError?.let {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(Color(0x22D9524A), RoundedCornerShape(8.dp))
                        .padding(12.dp)
                ) {
                    Text(it, color = StatusRed, style = MaterialTheme.typography.bodySmall)
                }
            }

            Spacer(Modifier.height(28.dp))

            // STOP PROCESSION with Confirmation Dialog
            OutlinedButton(
                onClick = { showStopConfirmationDialog = true },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(52.dp),
                colors = ButtonDefaults.outlinedButtonColors(
                    contentColor = StatusRed,
                ),
                shape = RoundedCornerShape(10.dp),
            ) {
                Icon(
                    imageVector = Icons.Default.Stop,
                    contentDescription = null,
                    tint = StatusRed,
                    modifier = Modifier.size(20.dp),
                )
                Spacer(Modifier.width(8.dp))
                Text(
                    "STOP PROCESSION",
                    color = StatusRed,
                    style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold),
                )
            }
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
            ProcessionState.values().forEach { state ->
                val isCurrent = state == currentState
                val isPast = currentState != null && state.ordinal < currentState.ordinal
                val color = when {
                    isCurrent -> Accent
                    isPast -> StatusGreen
                    else -> TextTertiary
                }
                Row(
                    modifier = Modifier.padding(vertical = 4.dp),
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
