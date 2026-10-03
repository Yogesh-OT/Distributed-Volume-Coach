package app.dvcoach.ui

import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Slider
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
import app.dvcoach.data.remote.ApiResult
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import kotlin.math.roundToInt

class ScheduleViewModel(private val repository: Repository) : ViewModel() {
    var wakeTime by mutableStateOf("07:00")
    var windowStart by mutableStateOf("09:00")
    var windowEnd by mutableStateOf("19:00")
    var quietStart by mutableStateOf("21:30")
    var quietEnd by mutableStateOf("07:00")
    var promptLimit by mutableIntStateOf(8)
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
            repository.profile.first()?.let {
                wakeTime = it.wakeTime
                windowStart = it.windowStart
                windowEnd = it.windowEnd
                quietStart = it.quietStart
                quietEnd = it.quietEnd
                promptLimit = it.promptLimit
            }
            loaded = true
        }
    }

    fun save() {
        busy = true
        error = null
        viewModelScope.launch {
            when (val result = repository.updateSchedule(wakeTime, windowStart, windowEnd, quietStart, quietEnd, promptLimit)) {
                is ApiResult.Ok -> saved = true
                is ApiResult.Failed -> error = result.message
            }
            busy = false
        }
    }
}

@Composable
fun ScheduleScreen(repository: Repository, onDone: () -> Unit) {
    val vm = repoViewModel(repository) { ScheduleViewModel(it) }
    LaunchedEffect(vm.saved) { if (vm.saved) onDone() }

    ScreenColumn {
        Text("Your day", style = MaterialTheme.typography.headlineMedium)
        Text(
            "Changes apply from your next check-in. Today's plan keeps the window it was made with.",
            style = MaterialTheme.typography.bodyMedium,
        )
        if (!vm.loaded) {
            CircularProgressIndicator()
            return@ScreenColumn
        }
        TimeField("Wake up", vm.wakeTime) { vm.wakeTime = it }
        TimeField("Training window starts", vm.windowStart) { vm.windowStart = it }
        TimeField("Training window ends", vm.windowEnd) { vm.windowEnd = it }
        TimeField("Quiet hours start", vm.quietStart) { vm.quietStart = it }
        TimeField("Quiet hours end", vm.quietEnd) { vm.quietEnd = it }
        Text("At most ${vm.promptLimit} prompts a day")
        Slider(
            value = vm.promptLimit.toFloat(),
            onValueChange = { vm.promptLimit = it.roundToInt() },
            valueRange = 1f..12f,
            steps = 10,
        )
        ErrorText(vm.error)
        Button(onClick = vm::save, enabled = !vm.busy, modifier = Modifier.fillMaxWidth()) {
            Text(if (vm.busy) "Saving…" else "Save")
        }
    }
}
