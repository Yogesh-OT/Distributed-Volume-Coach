package app.dvcoach.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Slider
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import app.dvcoach.data.Repository
import app.dvcoach.data.remote.ApiResult
import app.dvcoach.data.remote.OnboardingDto
import app.dvcoach.data.remote.ProfileDto
import kotlinx.coroutines.launch
import java.time.ZoneId
import kotlin.math.roundToInt

/**
 * Screening questions, paraphrased from the PAR-Q+ general health questions.
 * Keys match engine/safety.py. Check the PAR-Q+ Collaboration's terms before using the official wording.
 */
private val SCREENING_QUESTIONS = listOf(
    "heart_condition" to "Has a doctor ever said you have a heart condition or high blood pressure?",
    "chest_pain" to "Do you get chest pain at rest, in daily life, or when you're active?",
    "dizziness" to "In the past year, have you lost your balance from dizziness, or passed out?",
    "chronic_condition" to "Have you been diagnosed with another long-term medical condition?",
    "medication" to "Do you take prescribed medicine for a long-term condition?",
    "bone_joint_problem" to "Do you have a bone, joint or muscle problem that more activity could make worse?",
    "supervised_only" to "Has a doctor said you should only exercise under medical supervision?",
    "current_pain" to "Do you have pain anywhere right now?",
)

class OnboardingViewModel(private val repository: Repository) : ViewModel() {
    var goal by mutableStateOf("more_pushups")
    var trainingMonths by mutableStateOf("")
    var sex by mutableStateOf<String?>(null)
    var birthYear by mutableStateOf("")
    var confirmedAdult by mutableStateOf(false)
    var wakeTime by mutableStateOf("07:00")
    var windowStart by mutableStateOf("09:00")
    var windowEnd by mutableStateOf("19:00")
    var quietStart by mutableStateOf("21:30")
    var quietEnd by mutableStateOf("07:00")
    var promptLimit by mutableIntStateOf(8)
    val flags = mutableStateMapOf<String, Boolean>()
    var acceptedTerms by mutableStateOf(false)
    var busy by mutableStateOf(false)
        private set
    var message by mutableStateOf<String?>(null)
        private set

    fun submit() {
        val months = trainingMonths.toIntOrNull()
        val year = birthYear.toIntOrNull()
        message = when {
            months == null -> "Enter how many months you've trained regularly. 0 is fine."
            year == null || year !in 1900..2100 -> "Enter your birth year."
            !confirmedAdult -> "DV Coach is for people aged 18 and over."
            !acceptedTerms -> "Accept the terms to continue."
            else -> null
        }
        if (months == null || year == null || message != null) return

        busy = true
        viewModelScope.launch {
            val result = repository.onboard(
                OnboardingDto(
                    timezone = ZoneId.systemDefault().id,
                    birthYear = year,
                    confirmedAdult = true,
                    acceptedTerms = true,
                    profile = ProfileDto(
                        goal = goal,
                        trainingMonths = months,
                        sex = sex,
                        wakeTime = wakeTime,
                        windowStart = windowStart,
                        windowEnd = windowEnd,
                        quietStart = quietStart,
                        quietEnd = quietEnd,
                        promptLimit = promptLimit,
                        screeningFlags = flags.filterValues { it }.keys.sorted(),
                    ),
                )
            )
            // On success the saved profile moves the app on to the max test.
            if (result is ApiResult.Failed) message = result.message
            busy = false
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun OnboardingScreen(repository: Repository, modifier: Modifier = Modifier) {
    val vm = repoViewModel(repository) { OnboardingViewModel(it) }

    ScreenColumn(modifier) {
        Text("Welcome to DV Coach", style = MaterialTheme.typography.headlineMedium)
        Text(
            "Small sets of push-ups spread through your day, adjusted to how each one feels. A few questions first.",
            style = MaterialTheme.typography.bodyLarge,
        )

        Section("Your goal") {
            RadioRow("More push-ups", vm.goal == "more_pushups") { vm.goal = "more_pushups" }
            RadioRow("A daily strength habit", vm.goal == "strength_habit") { vm.goal = "strength_habit" }
        }

        Section("About you") {
            NumberField("Months of regular training", vm.trainingMonths, { vm.trainingMonths = it })
            NumberField("Birth year", vm.birthYear, { vm.birthYear = it })
            CheckRow("I'm 18 or older", vm.confirmedAdult) { vm.confirmedAdult = it }
            Text(
                "Sex (optional). Only used to pick reference ranges on your body profile.",
                style = MaterialTheme.typography.bodySmall,
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                listOf(null to "Not given", "male" to "Male", "female" to "Female").forEach { (value, label) ->
                    FilterChip(selected = vm.sex == value, onClick = { vm.sex = value }, label = { Text(label) })
                }
            }
        }

        Section("Your day") {
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
        }

        Section("Health check") {
            Text(
                "A yes doesn't stop you training. It means checking with a doctor before your first max test.",
                style = MaterialTheme.typography.bodySmall,
            )
            SCREENING_QUESTIONS.forEach { (key, question) ->
                SwitchRow(question, vm.flags[key] == true) { vm.flags[key] = it }
            }
        }

        CheckRow(
            "I understand this is training guidance, not medical advice, and I accept the terms.",
            vm.acceptedTerms,
        ) { vm.acceptedTerms = it }
        ErrorText(vm.message)
        Button(onClick = vm::submit, enabled = !vm.busy, modifier = Modifier.fillMaxWidth()) {
            Text(if (vm.busy) "Saving…" else "Continue")
        }
    }
}
