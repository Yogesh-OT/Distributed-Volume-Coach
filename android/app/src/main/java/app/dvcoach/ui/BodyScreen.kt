package app.dvcoach.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material3.Button
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedCard
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import app.dvcoach.data.Repository
import app.dvcoach.data.remote.ApiResult
import app.dvcoach.data.remote.BodyMeasurementDto
import app.dvcoach.data.remote.BodyProfileDto
import kotlinx.coroutines.launch

class BodyViewModel(private val repository: Repository) : ViewModel() {
    var height by mutableStateOf("")
    var weight by mutableStateOf("")
    var armSpan by mutableStateOf("")
    var waist by mutableStateOf("")
    var wrist by mutableStateOf("")
    var profile by mutableStateOf<BodyProfileDto?>(null)
        private set
    var error by mutableStateOf<String?>(null)
        private set
    var busy by mutableStateOf(false)
        private set

    init {
        viewModelScope.launch {
            when (val result = repository.bodyProfile()) {
                is ApiResult.Ok -> profile = result.value
                is ApiResult.Failed -> if (result.code != "no_measurements") error = result.message
            }
        }
    }

    fun save() {
        val measurements = BodyMeasurementDto(
            measuredOn = "", // the repository fills in today
            heightCm = height.toDoubleOrNull(),
            weightKg = weight.toDoubleOrNull(),
            armSpanCm = armSpan.toDoubleOrNull(),
            waistCm = waist.toDoubleOrNull(),
            wristCm = wrist.toDoubleOrNull(),
        )
        with(measurements) {
            if (listOf(heightCm, weightKg, armSpanCm, waistCm, wristCm).all { it == null }) {
                error = "Enter at least one measurement."
                return
            }
        }
        busy = true
        viewModelScope.launch {
            when (val result = repository.addMeasurements(measurements)) {
                is ApiResult.Ok -> {
                    profile = result.value
                    error = null
                    height = ""
                    weight = ""
                    armSpan = ""
                    waist = ""
                    wrist = ""
                }
                is ApiResult.Failed -> error = result.message
            }
            busy = false
        }
    }
}

@Composable
fun BodyScreen(repository: Repository) {
    val vm = repoViewModel(repository) { BodyViewModel(it) }

    ScreenColumn {
        Text("Body", style = MaterialTheme.typography.headlineMedium)
        vm.profile?.let { ProfileCard(it) }

        Section("Add measurements") {
            Text(
                "A tape measure and a scale, about three minutes. Leave out anything you'd rather not share. " +
                    "These describe your body. They never change today's plan.",
                style = MaterialTheme.typography.bodySmall,
            )
            NumberField("Height (cm)", vm.height, { vm.height = it }, decimal = true, supporting = "Against a wall, no shoes")
            NumberField("Weight (kg)", vm.weight, { vm.weight = it }, decimal = true, supporting = "In the morning, before eating")
            NumberField(
                "Arm span (cm)", vm.armSpan, { vm.armSpan = it }, decimal = true,
                supporting = "Arms straight out along a wall, fingertip to fingertip",
            )
            NumberField("Waist (cm)", vm.waist, { vm.waist = it }, decimal = true, supporting = "Tape at the navel, after breathing out")
            NumberField("Wrist (cm, optional)", vm.wrist, { vm.wrist = it }, decimal = true, supporting = "Just above the wrist bone")
            ErrorText(vm.error)
            Button(onClick = vm::save, enabled = !vm.busy, modifier = Modifier.fillMaxWidth()) {
                Text(if (vm.busy) "Saving…" else "Save")
            }
        }
    }
}

@Composable
private fun ProfileCard(profile: BodyProfileDto) {
    OutlinedCard(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("Your body profile", style = MaterialTheme.typography.titleLarge)
            Text(
                "Measured ${profile.measuredOn}",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            profile.lines.forEach { line ->
                HorizontalDivider()
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Text(
                        line.label,
                        modifier = Modifier.width(120.dp),
                        style = MaterialTheme.typography.labelLarge,
                        fontFamily = FontFamily.Monospace,
                    )
                    Column(modifier = Modifier.weight(1f)) {
                        Text(line.headline, style = MaterialTheme.typography.titleSmall)
                        Text(line.detail, style = MaterialTheme.typography.bodySmall)
                    }
                }
            }
        }
    }
}
