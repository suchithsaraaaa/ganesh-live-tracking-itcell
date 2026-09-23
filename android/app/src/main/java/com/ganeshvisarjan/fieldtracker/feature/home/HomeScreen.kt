package com.ganeshvisarjan.fieldtracker.feature.home

import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.ganeshvisarjan.fieldtracker.R
import com.ganeshvisarjan.fieldtracker.domain.model.AssignmentStatus
import com.ganeshvisarjan.fieldtracker.feature.assignment.AssignmentCard
import com.ganeshvisarjan.fieldtracker.ui.theme.TextSecondary

@Composable
fun HomeScreen(
    onOpenAssignment: () -> Unit,
    onOpenActiveTracking: () -> Unit,
    onOpenProfile: () -> Unit,
    viewModel: HomeViewModel = hiltViewModel(),
) {
    val state by viewModel.uiState.collectAsState()

    Column(modifier = Modifier.fillMaxSize().padding(20.dp)) {
        HomeHeader(state)

        androidx.compose.foundation.layout.Spacer(Modifier.height(20.dp))

        when {
            state.isLoading -> Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator()
            }
            state.assignment == null -> Card(modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(20.dp)) {
                    Text("No active assignment", style = MaterialTheme.typography.titleMedium)
                    Text(
                        "You will see your assigned GPID here once a station officer assigns one to you.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = TextSecondary,
                        modifier = Modifier.padding(top = 4.dp),
                    )
                }
            }
            else -> {
                AssignmentCard(assignment = state.assignment!!, onClick = onOpenAssignment)

                androidx.compose.foundation.layout.Spacer(Modifier.height(16.dp))

                if (state.activeSession != null) {
                    Text("Tracking active", style = MaterialTheme.typography.titleMedium, color = com.ganeshvisarjan.fieldtracker.ui.theme.Accent)
                    androidx.compose.foundation.layout.Spacer(Modifier.height(8.dp))
                    Button(onClick = onOpenActiveTracking, modifier = Modifier.fillMaxWidth().height(56.dp)) {
                        Text("OPEN ACTIVE TRACKING")
                    }
                } else if (state.assignment?.status == AssignmentStatus.ACTIVE) {
                    Button(onClick = onOpenAssignment, modifier = Modifier.fillMaxWidth().height(56.dp)) {
                        Text("VIEW ASSIGNMENT")
                    }
                }
            }
        }

        androidx.compose.foundation.layout.Spacer(Modifier.weight(1f))
        OutlinedButton(onClick = onOpenProfile, modifier = Modifier.fillMaxWidth()) {
            Text("PROFILE")
        }
    }
}

@Composable
private fun HomeHeader(state: HomeUiState) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier.fillMaxWidth(),
    ) {
        Image(
            painter = painterResource(id = R.drawable.ic_police_badge),
            contentDescription = null,
            modifier = Modifier
                .size(48.dp)
                .padding(end = 12.dp),
        )
        Column {
            Text(
                text = state.user?.displayName ?: "Field Officer",
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold,
            )
            Text(
                text = listOfNotNull(state.user?.role?.name, state.user?.policeStation, state.user?.zone).joinToString(" · "),
                style = MaterialTheme.typography.bodySmall,
                color = TextSecondary,
            )
        }
    }
}
