package com.ganeshvisarjan.fieldtracker.feature.profile

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.ganeshvisarjan.fieldtracker.ui.theme.TextSecondary

/**
 * Read-only officer info + Log Out (spec section 35 of the workflow doc). No
 * administrative user-management functionality — that remains a web/admin
 * responsibility.
 */
@Composable
fun ProfileScreen(
    onLoggedOut: () -> Unit,
    viewModel: ProfileViewModel = hiltViewModel(),
) {
    val state by viewModel.uiState.collectAsState()

    LaunchedEffect(state.loggedOut) {
        if (state.loggedOut) onLoggedOut()
    }

    Column(modifier = Modifier.fillMaxSize().padding(20.dp)) {
        Text("Profile", style = MaterialTheme.typography.headlineMedium)
        androidx.compose.foundation.layout.Spacer(Modifier.height(20.dp))

        ProfileField("Name", state.user?.displayName)
        ProfileField("Username", state.user?.username)
        ProfileField("Role", state.user?.role?.name)
        ProfileField("Police Station", state.user?.policeStation)
        ProfileField("Zone", state.user?.zone)

        androidx.compose.foundation.layout.Spacer(Modifier.weight(1f))
        Button(onClick = viewModel::logout, modifier = Modifier.fillMaxWidth().height(56.dp)) {
            Text("LOG OUT")
        }
    }
}

@Composable
private fun ProfileField(label: String, value: String?) {
    Column(Modifier.padding(bottom = 16.dp)) {
        Text(label, style = MaterialTheme.typography.labelSmall, color = TextSecondary)
        Text(value ?: "—", style = MaterialTheme.typography.bodyLarge)
    }
}
