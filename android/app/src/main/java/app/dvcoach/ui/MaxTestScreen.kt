package app.dvcoach.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.selection.selectable
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import app.dvcoach.data.Repository
import app.dvcoach.data.remote.ApiResult
import app.dvcoach.engine.Levels
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

class MaxTestViewModel(private val repository: Repository) : ViewModel() {
    var reps by mutableStateOf("")
    var level by mutableIntStateOf(Levels.DEFAULT)
    var clearanceChecked by mutableStateOf(false)
    var busy by mutableStateOf(false)
        private set
    var error by mutableStateOf<String?>(null)
        private set
    var info by mutableStateOf<String?>(null)
        private set
    var needsClearance by mutableStateOf(false)
        private set
    /** Advice to test an easier or harder level next time, shown before leaving the screen. */
    var suggestion by mutableStateOf<String?>(null)
        private set
    var saved by mutableStateOf(false)
        private set

    init {
        viewModelScope.launch { repository.profile.first()?.let { level = it.level } }
    }

    fun submit() {
        val n = reps.toIntOrNull()
        if (n == null || n !in 1..500) {
            error = "Enter how many you did."
            return
        }
        busy = true
        viewModelScope.launch {
            when (val result = repository.recordMaxTest(n, level)) {
                is ApiResult.Ok -> {
                    error = null
                    suggestion = result.value.suggestion?.message
                    if (suggestion == null) saved = true
                }
                is ApiResult.Failed -> {
                    error = result.message + (result.nextAllowed?.let { " Your next test at this level can be on $it." } ?: "")
                    needsClearance = result.code == "clearance_required"
                }
            }
            busy = false
        }
    }

    fun acknowledgeSuggestion() {
        suggestion = null
        saved = true
    }

    fun confirmClearance() {
        busy = true
        viewModelScope.launch {
            when (val result = repository.confirmClearance()) {
                is ApiResult.Ok -> {
                    needsClearance = false
                    error = null
                    info = "Saved. You can do the max test now."
                }
                is ApiResult.Failed -> error = result.message
            }
            busy = false
        }
    }
}

/** The first time, saving moves the app on by itself. A retest passes [onDone] to go back. */
@Composable
fun MaxTestScreen(repository: Repository, modifier: Modifier = Modifier, onDone: (() -> Unit)? = null) {
    val vm = repoViewModel(repository) { MaxTestViewModel(it) }
    LaunchedEffect(vm.saved) { if (vm.saved) onDone?.invoke() }
    val chosen = Levels.of(vm.level)

    ScreenColumn(modifier) {
        Text("Max test", style = MaterialTheme.typography.headlineMedium)
        Text(
            "This sizes your daily sets. Each set is a bit under half of what you do here.",
            style = MaterialTheme.typography.bodyLarge,
        )

        Section("Which version?") {
            Text(
                "Pick the hardest one you can do at least 5 of with good form. You can change level any time.",
                style = MaterialTheme.typography.bodySmall,
            )
            Levels.ALL.forEach { level ->
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .selectable(selected = vm.level == level.number, onClick = { vm.level = level.number }, role = Role.RadioButton)
                        .padding(vertical = 4.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    RadioButton(selected = vm.level == level.number, onClick = null)
                    Column(modifier = Modifier.padding(start = 12.dp)) {
                        Text(level.title)
                        Text(level.how, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }
        }

        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("1. Warm up with a few easy reps, then rest for two minutes.")
                Text("2. Do one set of ${chosen.plural} with good form: body straight, full range.")
                Text("3. Stop when you have 0 or 1 reps left in the tank.")
                Text(
                    "Stop straight away if you feel pain, dizziness or chest discomfort.",
                    color = MaterialTheme.colorScheme.error,
                )
            }
        }
        NumberField("${chosen.title}s done", vm.reps, { vm.reps = it })
        ErrorText(vm.error)
        vm.info?.let { Text(it, color = MaterialTheme.colorScheme.primary) }
        if (vm.needsClearance) {
            CheckRow("A doctor has cleared me for exercise", vm.clearanceChecked) { vm.clearanceChecked = it }
            OutlinedButton(onClick = vm::confirmClearance, enabled = vm.clearanceChecked && !vm.busy) {
                Text("Confirm clearance")
            }
        }
        Button(onClick = vm::submit, enabled = !vm.busy, modifier = Modifier.fillMaxWidth()) {
            Text(if (vm.busy) "Saving…" else "Save max test")
        }
    }

    vm.suggestion?.let { message ->
        AlertDialog(
            onDismissRequest = vm::acknowledgeSuggestion,
            title = { Text("Saved") },
            text = { Text(message) },
            confirmButton = { TextButton(onClick = vm::acknowledgeSuggestion) { Text("OK") } },
        )
    }
}
