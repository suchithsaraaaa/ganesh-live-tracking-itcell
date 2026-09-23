package com.ganeshvisarjan.fieldtracker.feature.debug

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.ganeshvisarjan.fieldtracker.ui.theme.TextSecondary

@Composable
fun DebugScreen(viewModel: DebugViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()

    val rows = listOf(
        "Environment" to state.environment,
        "API base URL" to state.apiBaseUrl,
        "Authenticated" to state.isAuthenticated.toString(),
        "Active GPID" to (state.activeGpid ?: "—"),
        "Tracking session" to (state.activeSessionId ?: "—"),
        "Last GPS accuracy" to (state.lastFixAccuracy?.let { "±${it}m" } ?: "—"),
        "Last GPS timestamp" to (state.lastFixTimestamp?.toString() ?: "—"),
        "Pending telemetry" to state.pendingTelemetry.toString(),
        "Network" to state.networkState,
    )

    LazyColumn(modifier = Modifier.fillMaxSize().padding(20.dp)) {
        item {
            Text("Debug", style = MaterialTheme.typography.headlineMedium)
            androidx.compose.foundation.layout.Spacer(Modifier.padding(top = 12.dp))
        }
        items(rows) { (label, value) ->
            Column(Modifier.padding(bottom = 12.dp)) {
                Text(label, style = MaterialTheme.typography.labelSmall, color = TextSecondary)
                Text(value, style = MaterialTheme.typography.bodyMedium)
            }
        }
    }
}
