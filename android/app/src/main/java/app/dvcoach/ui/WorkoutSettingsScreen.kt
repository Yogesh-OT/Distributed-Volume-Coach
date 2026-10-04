package app.dvcoach.ui

import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.selection.toggleable
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.Role
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import app.dvcoach.data.Repository
import app.dvcoach.data.remote.ApiResult
import app.dvcoach.data.remote.SessionSettingsDto
import kotlinx.coroutines.launch

/** Household items, matching engine.exercises.Need on the server. */
private val ITEMS = listOf(
    "wall" to "A wall",
    "chair" to "A sturdy chair, sofa or bed edge",
    "doorway" to "A doorway you can hold on to",
    "smooth_floor" to "A towel or socks that slide on your floor",
    "table" to "A sturdy table you can lie under (not glass, not folding)",
    "step" to "A stair or sturdy step",
    "sofa" to "A sofa heavy enough to hook your feet under",
)
private val EVERYDAY = setOf("wall", "chair", "doorway", "smooth_floor")

class WorkoutSettingsViewModel(private val repository: Repository) : ViewModel() {
    var goal by mutableStateOf("muscle")
    var days by mutableIntStateOf(3)
    var minutes by mutableIntStateOf(30)
    var available by mutableStateOf(EVERYDAY)
    var highImpact by mutableStateOf(false)
    var loaded by mutableStateOf(false)
        private set
    var busy by mutableStateOf(false)
        private set
    var error by mutableStateOf<String?>(null)
        private set
    var saved by mutableStateOf(false)
        private set

    init {
        viewModelScope.launch {
            when (val result = repository.sessionSettings()) {
                is ApiResult.Ok -> result.value.let {
                    goal = it.goal
                    days = it.daysPerWeek
                    minutes = it.sessionMinutes
                    available = it.available?.toSet() ?: EVERYDAY
                    highImpact = it.highImpact
                }
                // Not set up yet: keep the defaults. Anything else is worth showing.
                is ApiResult.Failed -> if (result.code != "session_settings_required") error = result.message
            }
            loaded = true
        }
    }

    fun toggle(item: String, on: Boolean) {
        available = if (on) available + item else available - item
    }

    fun save() {
        busy = true
        error = null
        viewModelScope.launch {
            // Weekdays are left to the server, which spreads the days evenly.
            val settings = SessionSettingsDto(
                goal = goal,
                daysPerWeek = days,
                sessionMinutes = minutes,
                available = available.sorted(),
                highImpact = highImpact,
            )
            when (val result = repository.saveSessionSettings(settings)) {
                is ApiResult.Ok -> saved = true
                is ApiResult.Failed -> error = result.message
            }
            busy = false
        }
    }
}

@Composable
fun WorkoutSettingsScreen(repository: Repository, onDone: () -> Unit) {
    val vm = repoViewModel(repository) { WorkoutSettingsViewModel(it) }
    LaunchedEffect(vm.saved) { if (vm.saved) onDone() }

    ScreenColumn {
        Text("Workouts", style = MaterialTheme.typography.headlineMedium)
        Text(
            "Short sessions of bodyweight exercises in pairs, with 60 seconds of rest. " +
                "3 days of 30 minutes is a good start: about 10 sets a week for each big muscle.",
            style = MaterialTheme.typography.bodyMedium,
        )
        if (!vm.loaded) {
            CircularProgressIndicator()
            return@ScreenColumn
        }

        Section("Your goal") {
            Choice("Build muscle", vm.goal == "muscle") { vm.goal = "muscle" }
            Choice("Get fit and lose fat (adds short cardio circuits)", vm.goal == "fit") { vm.goal = "fit" }
        }
        Section("Days a week") {
            for (d in listOf(2, 3, 4)) Choice("$d days", vm.days == d) { vm.days = d }
        }
        Section("Session length") {
            for (m in listOf(20, 30, 45)) Choice("$m minutes", vm.minutes == m) { vm.minutes = m }
        }
        Section("What you have at home") {
            Text(
                "Exercises that need something you don't have are skipped, and harder versions unlock as you tick more.",
                style = MaterialTheme.typography.bodySmall,
            )
            for ((key, label) in ITEMS) Tick(label, key in vm.available) { vm.toggle(key, it) }
        }
        Section("Impact") {
            Tick("Jumping moves are fine (louder, harder on the joints)", vm.highImpact) { vm.highImpact = it }
        }

        ErrorText(vm.error)
        Button(onClick = vm::save, enabled = !vm.busy, modifier = Modifier.fillMaxWidth()) {
            Text(if (vm.busy) "Saving…" else "Save")
        }
    }
}

@Composable
private fun Choice(label: String, selected: Boolean, onClick: () -> Unit) {
    Row(
        Modifier.fillMaxWidth().selectable(selected = selected, onClick = onClick, role = Role.RadioButton),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        RadioButton(selected = selected, onClick = null)
        Text(label)
    }
}

@Composable
private fun Tick(label: String, checked: Boolean, onChange: (Boolean) -> Unit) {
    Row(
        Modifier.fillMaxWidth().toggleable(value = checked, onValueChange = onChange, role = Role.Checkbox),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Checkbox(checked = checked, onCheckedChange = null)
        Text(label)
    }
}
