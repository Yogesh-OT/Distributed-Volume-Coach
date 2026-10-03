package app.dvcoach.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

private val GUIDE = listOf(
    "Set up" to listOf(
        "Hands on the floor slightly wider than your shoulders, fingers pointing forward.",
        "Body in one straight line from head to heels. Brace your stomach and squeeze your glutes.",
    ),
    "Down" to listOf(
        "Bend your elbows so they angle back at about 45° from your body, not straight out to the sides.",
        "Lower until your chest is about a fist's height from the floor.",
    ),
    "Up" to listOf(
        "Push the floor away until your arms are straight, keeping the straight line.",
        "Breathe out on the way up.",
    ),
    "Common mistakes" to listOf(
        "Hips sagging or sticking up.",
        "Elbows flared straight out.",
        "Half reps that stop well above the floor.",
        "Head dropping towards the floor.",
    ),
    "Make it easier or harder" to listOf(
        "Easier: hands on a table, bench or wall. The higher the hands, the easier it is.",
        "Harder, later on: feet raised on a step.",
    ),
    "What it works" to listOf(
        "Chest, the front of your shoulders and triceps. Your core holds the straight line.",
    ),
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PushupGuideSheet(onDismiss: () -> Unit) {
    ModalBottomSheet(onDismissRequest = onDismiss) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .verticalScroll(rememberScrollState())
                .padding(start = 24.dp, end = 24.dp, bottom = 32.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            Text("How to do a push-up", style = MaterialTheme.typography.headlineSmall)
            GUIDE.forEach { (title, points) ->
                Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(title, style = MaterialTheme.typography.titleMedium)
                    points.forEach { Text("•  $it", style = MaterialTheme.typography.bodyMedium) }
                }
            }
            Text(
                "Stop if you feel sharp pain, dizziness or chest discomfort.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.error,
            )
        }
    }
}
