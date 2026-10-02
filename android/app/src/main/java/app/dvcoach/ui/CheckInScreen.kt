package app.dvcoach.ui

import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import app.dvcoach.data.Repository
import kotlinx.coroutines.launch

class CheckInViewModel(private val repository: Repository) : ViewModel() {
    var sleep by mutableIntStateOf(3)
    var soreness by mutableIntStateOf(2)
    var energy by mutableIntStateOf(3)
    var busy by mutableStateOf(false)
        private set
    var error by mutableStateOf<String?>(null)
        private set
    var finished by mutableStateOf(false)
        private set

    fun submit() {
        busy = true
        error = null
        viewModelScope.launch {
            when (val outcome = repository.checkIn(sleep, soreness, energy)) {
                is Repository.CheckInOutcome.Planned -> finished = true
                is Repository.CheckInOutcome.Failed -> error = outcome.message
            }
            busy = false
        }
    }
}

@Composable
fun CheckInScreen(repository: Repository, onDone: () -> Unit) {
    val vm = repoViewModel(repository) { CheckInViewModel(it) }
    LaunchedEffect(vm.finished) { if (vm.finished) onDone() }

    ScreenColumn {
        Text("Morning check-in", style = MaterialTheme.typography.headlineMedium)
        Text(
            "Today's plan is built from these answers and your latest max test.",
            style = MaterialTheme.typography.bodyLarge,
        )
        ScaleRow("How did you sleep?", "1 · badly", "5 · great", vm.sleep) { vm.sleep = it }
        ScaleRow("How sore are you?", "1 · not at all", "5 · very", vm.soreness) { vm.soreness = it }
        ScaleRow("How's your energy?", "1 · low", "5 · high", vm.energy) { vm.energy = it }
        ErrorText(vm.error)
        Button(onClick = vm::submit, enabled = !vm.busy, modifier = Modifier.fillMaxWidth()) {
            Text(if (vm.busy) "Building your plan…" else "Get today's plan")
        }
    }
}
