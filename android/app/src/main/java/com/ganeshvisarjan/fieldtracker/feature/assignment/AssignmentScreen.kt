package com.ganeshvisarjan.fieldtracker.feature.assignment

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
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import com.ganeshvisarjan.fieldtracker.domain.usecase.ValidateProcessionStartUseCase.Result as Readiness
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

                    Spacer(Modifier.height(20.dp))

                    if (!state.hasPreciseLocationPermission) {
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            colors = CardDefaults.cardColors(containerColor = Color(0x22D9524A)),
                            shape = RoundedCornerShape(12.dp),
                        ) {
                            Column(Modifier.padding(16.dp)) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Icon(
                                        imageVector = Icons.Default.Warning,
                                        contentDescription = null,
                                        tint = StatusRed,
                                    )
                                    Spacer(Modifier.width(8.dp))
                                    Text(
                                        "Precise Location Required",
                                        style = MaterialTheme.typography.titleSmall,
                                        color = StatusRed,
                                    )
                                }
                                Spacer(Modifier.height(6.dp))
                                Text(
                                    "Precise GPS location permission is required before you can start tracking this procession.",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = TextSecondary,
                                )
                                Spacer(Modifier.height(12.dp))
                                OutlinedButton(
                                    onClick = viewModel::refreshPermissionState,
                                    modifier = Modifier.fillMaxWidth(),
                                ) {
                                    Text("CHECK PERMISSIONS AGAIN")
                                }
                            }
                        }
                        return@Column
                    }

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
                                .padding(12.dp)
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
private fun ReadinessSummary(readiness: Readiness?) {
    when (readiness) {
        null -> Text(
            "Tap Check Location to acquire a fresh GPS fix before starting the procession.",
            color = TextSecondary,
            style = MaterialTheme.typography.bodySmall,
        )
        is Readiness.WaitingForGps -> Text(
            "Getting your current GPS fix…",
            color = TextSecondary,
            style = MaterialTheme.typography.bodySmall,
        )
        is Readiness.GpsAccuracyTooLow -> Text(
            "GPS accuracy too low (±${readiness.accuracyMeters.toInt()}m). Move to an open sky area for better satellite reception.",
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
                    "GPS fix acquired (±${readiness.accuracyMeters.toInt()}m). Ready to start!",
                    color = StatusGreen,
                    style = MaterialTheme.typography.bodySmall.copy(fontWeight = FontWeight.Medium),
                )
            }
        }
    }
}
