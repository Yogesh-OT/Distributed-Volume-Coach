package app.dvcoach.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import app.dvcoach.data.Repository
import app.dvcoach.data.remote.ApiResult
import app.dvcoach.data.remote.DayDto
import app.dvcoach.data.remote.ProgressDto
import kotlinx.coroutines.launch
import java.time.LocalDate
import java.time.format.DateTimeFormatter

private const val CHART_DAYS = 14L
private const val MAX_TEST_INTERVAL_DAYS = 14L

sealed interface ProgressUi {
    data object Loading : ProgressUi
    data class Loaded(val progress: ProgressDto) : ProgressUi
    data class Failed(val message: String) : ProgressUi
}

class ProgressViewModel(private val repository: Repository) : ViewModel() {
    var state by mutableStateOf<ProgressUi>(ProgressUi.Loading)
        private set
    var deleteError by mutableStateOf<String?>(null)
        private set

    val today: LocalDate get() = repository.today()

    init {
        refresh()
    }

    fun refresh() {
        state = ProgressUi.Loading
        viewModelScope.launch {
            state = when (val result = repository.progress()) {
                is ApiResult.Ok -> ProgressUi.Loaded(result.value)
                is ApiResult.Failed -> ProgressUi.Failed(result.message)
            }
        }
    }

    /** On success the cleared profile sends the app back to onboarding. */
    fun deleteAccount() {
        viewModelScope.launch {
            val result = repository.deleteAccount()
            if (result is ApiResult.Failed) deleteError = result.message
        }
    }
}

@Composable
fun ProgressScreen(repository: Repository, onRetest: () -> Unit) {
    val vm = repoViewModel(repository) { ProgressViewModel(it) }
    var confirmDelete by remember { mutableStateOf(false) }

    ScreenColumn {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text("Progress", style = MaterialTheme.typography.headlineMedium, modifier = Modifier.weight(1f))
            TextButton(onClick = vm::refresh) { Text("Refresh") }
        }
        when (val state = vm.state) {
            ProgressUi.Loading -> CircularProgressIndicator()
            is ProgressUi.Failed -> ErrorText(state.message)
            is ProgressUi.Loaded -> ProgressContent(state.progress, vm.today, onRetest)
        }

        HorizontalDivider()
        Section("Account") {
            Text(
                "Delete your account and everything stored about you, on the server and on this phone.",
                style = MaterialTheme.typography.bodySmall,
            )
            OutlinedButton(
                onClick = { confirmDelete = true },
                colors = ButtonDefaults.outlinedButtonColors(contentColor = MaterialTheme.colorScheme.error),
            ) { Text("Delete my account and data") }
            ErrorText(vm.deleteError)
        }
        ServerAddressCard(repository)
    }

    if (confirmDelete) {
        AlertDialog(
            onDismissRequest = { confirmDelete = false },
            title = { Text("Delete everything?") },
            text = { Text("This removes your profile, plans and logs for good. It can't be undone.") },
            confirmButton = {
                TextButton(onClick = {
                    confirmDelete = false
                    vm.deleteAccount()
                }) { Text("Delete") }
            },
            dismissButton = { TextButton(onClick = { confirmDelete = false }) { Text("Cancel") } },
        )
    }
}

@Composable
private fun ProgressContent(progress: ProgressDto, today: LocalDate, onRetest: () -> Unit) {
    val latest = progress.maxTests.lastOrNull()
    Section("Max test") {
        Text(latest?.let { "${it.reps} push-ups on ${it.testedOn}" } ?: "No max test yet.")
        if (progress.maxTests.size > 1) {
            Text("History: " + progress.maxTests.joinToString(" → ") { "${it.reps}" }, style = MaterialTheme.typography.bodySmall)
        }
        val nextTest = latest?.let { LocalDate.parse(it.testedOn).plusDays(MAX_TEST_INTERVAL_DAYS) }
        if (nextTest == null || !today.isBefore(nextTest)) {
            Button(onClick = onRetest) { Text("Take a new max test") }
        } else {
            Text("Your next max test can be on $nextTest.", style = MaterialTheme.typography.bodySmall)
        }
    }

    Section("Last 14 days") {
        RepsChart(progress.days, today)
        val recent = progress.days.filter { !LocalDate.parse(it.date).isBefore(today.minusDays(CHART_DAYS - 1)) }
        val sets = recent.sumOf { it.setsDone }
        val hard = recent.sumOf { it.hardSets }
        Text(
            "$sets sets done, $hard rated hard" + if (sets > 0) " (${hard * 100 / sets}%)." else ".",
            style = MaterialTheme.typography.bodyMedium,
        )
    }

    progress.weights.lastOrNull()?.let {
        Section("Weight") { Text("${it.weightKg} kg on ${it.measuredOn}") }
    }
}

@Composable
private fun RepsChart(days: List<DayDto>, today: LocalDate) {
    val byDate = days.associate { it.date to it.repsDone }
    val dates = (CHART_DAYS - 1 downTo 0L).map { today.minusDays(it) }
    val values = dates.map { byDate[it.toString()] ?: 0 }
    val top = (values.maxOrNull() ?: 0).coerceAtLeast(1)
    val barColor = MaterialTheme.colorScheme.primary
    val emptyColor = MaterialTheme.colorScheme.surfaceVariant

    Canvas(
        modifier = Modifier
            .fillMaxWidth()
            .height(120.dp)
            .semantics { contentDescription = "Push-ups per day for the last 14 days. Most in a day: $top." },
    ) {
        val slot = size.width / values.size
        val barWidth = slot * 0.6f
        values.forEachIndexed { i, reps ->
            val h = if (reps == 0) 3.dp.toPx() else size.height * reps / top
            drawRoundRect(
                color = if (reps == 0) emptyColor else barColor,
                topLeft = Offset(i * slot + (slot - barWidth) / 2, size.height - h),
                size = Size(barWidth, h),
                cornerRadius = CornerRadius(3.dp.toPx()),
            )
        }
    }
    val format = DateTimeFormatter.ofPattern("d MMM")
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(dates.first().format(format), style = MaterialTheme.typography.labelSmall)
        Text("Tallest bar: $top reps", style = MaterialTheme.typography.labelSmall)
        Text("Today", style = MaterialTheme.typography.labelSmall)
    }
}
