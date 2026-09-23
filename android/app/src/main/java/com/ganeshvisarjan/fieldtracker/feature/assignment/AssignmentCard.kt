package com.ganeshvisarjan.fieldtracker.feature.assignment

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import com.ganeshvisarjan.fieldtracker.domain.model.Assignment
import com.ganeshvisarjan.fieldtracker.domain.model.HeightClass
import com.ganeshvisarjan.fieldtracker.ui.theme.StatusBlue
import com.ganeshvisarjan.fieldtracker.ui.theme.StatusGreen
import com.ganeshvisarjan.fieldtracker.ui.theme.StatusRed
import com.ganeshvisarjan.fieldtracker.ui.theme.StatusYellow
import com.ganeshvisarjan.fieldtracker.ui.theme.TextSecondary

fun HeightClass.color(): Color = when (this) {
    HeightClass.GREEN -> StatusGreen
    HeightClass.YELLOW -> StatusYellow
    HeightClass.RED -> StatusRed
    HeightClass.BELOW_OPERATIONAL_THRESHOLD -> StatusBlue
    HeightClass.UNKNOWN -> TextSecondary
}

fun HeightClass.label(): String = when (this) {
    HeightClass.GREEN -> "GREEN"
    HeightClass.YELLOW -> "YELLOW"
    HeightClass.RED -> "RED"
    HeightClass.BELOW_OPERATIONAL_THRESHOLD -> "BELOW THRESHOLD"
    HeightClass.UNKNOWN -> "UNKNOWN"
}

@Composable
fun AssignmentCard(assignment: Assignment, onClick: () -> Unit, modifier: Modifier = Modifier) {
    Card(
        onClick = onClick,
        modifier = modifier.fillMaxWidth(),
    ) {
        Column(Modifier.padding(20.dp)) {
            Text("GPID", style = MaterialTheme.typography.labelSmall, color = TextSecondary)
            Text(
                assignment.idol.gpid,
                style = MaterialTheme.typography.headlineMedium,
                fontFamily = FontFamily.Monospace,
            )

            androidx.compose.foundation.layout.Spacer(Modifier.padding(top = 8.dp))

            Row {
                assignment.idol.heightFeet?.let {
                    Text(
                        "${it.toInt()} ft",
                        style = MaterialTheme.typography.titleMedium,
                        modifier = Modifier.padding(end = 12.dp),
                    )
                }
                HeightBadge(assignment.idol.heightClass)
            }

            androidx.compose.foundation.layout.Spacer(Modifier.padding(top = 12.dp))

            LabeledLine("FROM", assignment.idol.originAddress ?: "—")
            LabeledLine("TO", assignment.idol.destinationAddress ?: "—")
            LabeledLine("STATUS", assignment.status.name)
        }
    }
}

@Composable
private fun HeightBadge(heightClass: HeightClass) {
    Text(
        text = heightClass.label(),
        color = heightClass.color(),
        style = MaterialTheme.typography.labelLarge,
        modifier = Modifier
            .background(heightClass.color().copy(alpha = 0.15f), RoundedCornerShape(4.dp))
            .padding(horizontal = 8.dp, vertical = 4.dp),
    )
}

@Composable
private fun LabeledLine(label: String, value: String) {
    Column(Modifier.padding(top = 8.dp)) {
        Text(label, style = MaterialTheme.typography.labelSmall, color = TextSecondary)
        Text(value, style = MaterialTheme.typography.bodyLarge)
    }
}
