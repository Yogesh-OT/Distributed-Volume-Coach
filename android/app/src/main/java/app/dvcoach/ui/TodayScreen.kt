package app.dvcoach.ui

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import app.dvcoach.data.Repository
import app.dvcoach.data.local.PlanEntity
import app.dvcoach.engine.DayState
import app.dvcoach.engine.DayStatus
import app.dvcoach.engine.Rating
import app.dvcoach.engine.SetState
import app.dvcoach.engine.SetStatus
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

class TodayViewModel(private val repository: Repository) : ViewModel() {
    val today: StateFlow<Repository.Today?> =
        repository.observeToday().stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), null)

    fun log(date: String, ref: String, rating: Rating) {
        viewModelScope.launch { repository.logSet(date, ref, rating) }
    }
}

@Composable
fun TodayScreen(repository: Repository, onCheckIn: () -> Unit) {
    val vm = repoViewModel(repository) { TodayViewModel(it) }
    val today by vm.today.collectAsStateWithLifecycle()

    ScreenColumn {
        Text("Today", style = MaterialTheme.typography.headlineMedium)
        NotificationPermissionCard()
        val t = today
        when {
            t == null -> CircularProgressIndicator()
            t.plan == null -> CheckInCard(checkedIn = t.checkedIn, onCheckIn = onCheckIn)
            else -> PlanSection(t.date, t.plan, t.day, onLog = vm::log)
        }
    }
}

@Composable
private fun NotificationPermissionCard() {
    if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) return
    val context = LocalContext.current
    var granted by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) ==
                PackageManager.PERMISSION_GRANTED
        )
    }
    val launcher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted = it }
    if (granted) return

    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Turn on notifications", style = MaterialTheme.typography.titleMedium)
            Text("Each set arrives as a notification you can log from. Without them, you'd need to open the app to see when the next set is due.")
            Button(onClick = { launcher.launch(Manifest.permission.POST_NOTIFICATIONS) }) { Text("Allow notifications") }
        }
    }
}

@Composable
private fun CheckInCard(checkedIn: Boolean, onCheckIn: () -> Unit) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Morning check-in", style = MaterialTheme.typography.titleMedium)
            Text(
                if (checkedIn) "Your answers are saved, but the plan didn't arrive. Try again."
                else "Three quick questions, then today's plan."
            )
            Button(onClick = onCheckIn) { Text(if (checkedIn) "Try again" else "Check in") }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun PlanSection(date: String, plan: PlanEntity, day: DayState?, onLog: (String, String, Rating) -> Unit) {
    Text(plan.reason, style = MaterialTheme.typography.bodyLarge)
    if (plan.source == "fallback") Banner("Offline plan. It syncs when you're back online.")
    if (plan.kind == "mobility") {
        Banner("Rest day: gentle mobility only.")
        return
    }
    if (day == null || day.sets.isEmpty()) return

    when (day.status) {
        DayStatus.COMPLETE -> Banner("All done for today. Nice work.")
        DayStatus.ENDED_HARD -> Banner("Two hard sets: that's enough for today. Rest and come back tomorrow.")
        DayStatus.STOPPED_PAIN -> Banner(
            "Push-ups are stopped for today because of pain. If it comes back, check with a professional.",
            isError = true,
        )
        DayStatus.ACTIVE -> Unit
    }

    val next = if (day.status == DayStatus.ACTIVE) day.nextPending else null
    if (next != null) {
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text("Next: ${next.targetReps} push-ups at ${next.at}", style = MaterialTheme.typography.titleMedium)
                Text(
                    "Any time around then is fine. Hard means 0 or 1 reps were left. Pain stops push-ups for today.",
                    style = MaterialTheme.typography.bodySmall,
                )
                FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    FilledTonalButton(onClick = { onLog(date, next.ref, Rating.EASY) }) { Text("Easy") }
                    Button(onClick = { onLog(date, next.ref, Rating.SOLID) }) { Text("Solid") }
                    FilledTonalButton(onClick = { onLog(date, next.ref, Rating.HARD) }) { Text("Hard") }
                    OutlinedButton(onClick = { onLog(date, next.ref, Rating.PAIN) }) { Text("Pain") }
                    TextButton(onClick = { onLog(date, next.ref, Rating.SKIPPED) }) { Text("Skip") }
                }
            }
        }
    }

    Text("Today's sets", style = MaterialTheme.typography.titleMedium)
    Column {
        day.sets.forEach { SetRow(it, isNext = it.ref == next?.ref) }
    }
}

@Composable
private fun SetRow(set: SetState, isNext: Boolean) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(set.at, fontFamily = FontFamily.Monospace, modifier = Modifier.width(64.dp))
        Text(
            "${set.targetReps} reps",
            modifier = Modifier.weight(1f),
            textDecoration = if (set.status == SetStatus.DROPPED) TextDecoration.LineThrough else null,
        )
        StatusChip(set, isNext)
    }
    HorizontalDivider()
}

@Composable
private fun StatusChip(set: SetState, isNext: Boolean) {
    val colors = MaterialTheme.colorScheme
    val (label, background) = when (set.status) {
        SetStatus.LOGGED -> when (set.rating) {
            Rating.EASY -> "Easy" to colors.primaryContainer
            Rating.SOLID, null -> "Done" to colors.primaryContainer
            Rating.HARD -> "Hard" to colors.errorContainer
            Rating.PAIN -> "Pain" to colors.errorContainer
            Rating.SKIPPED -> "Skipped" to colors.surfaceVariant
        }
        SetStatus.MISSED -> "Missed" to colors.surfaceVariant
        SetStatus.DROPPED -> "Dropped" to colors.surfaceVariant
        SetStatus.PENDING -> (if (isNext) "Up next" else "Planned") to
            (if (isNext) colors.secondaryContainer else colors.surfaceVariant)
    }
    Surface(color = background, shape = MaterialTheme.shapes.small) {
        Text(label, modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp), style = MaterialTheme.typography.labelMedium)
    }
}
