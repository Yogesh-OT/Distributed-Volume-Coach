package app.dvcoach.ui

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.provider.Settings
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
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.LifecycleEventEffect
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import app.dvcoach.core.Hhmm
import app.dvcoach.data.Repository
import app.dvcoach.data.local.LocalProfile
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

    val profile: StateFlow<LocalProfile?> =
        repository.profile.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), null)

    var remindersOnTime by mutableStateOf(repository.remindersOnTime())
        private set

    fun log(date: String, ref: String, rating: Rating) {
        viewModelScope.launch { repository.logSet(date, ref, rating) }
    }

    /** Called when the screen comes back, for example from the Alarms & reminders settings page. */
    fun refreshReminders() {
        val onTime = repository.remindersOnTime()
        if (onTime && !remindersOnTime) viewModelScope.launch { repository.rescheduleAll() }
        remindersOnTime = onTime
    }
}

@Composable
fun TodayScreen(repository: Repository, onCheckIn: () -> Unit, onEditSchedule: () -> Unit) {
    val vm = repoViewModel(repository) { TodayViewModel(it) }
    val today by vm.today.collectAsStateWithLifecycle()
    val profile by vm.profile.collectAsStateWithLifecycle()
    LifecycleEventEffect(Lifecycle.Event.ON_RESUME) { vm.refreshReminders() }

    ScreenColumn {
        Text("Today", style = MaterialTheme.typography.headlineMedium)
        profile?.let { WindowLine(it, onEditSchedule) }
        NotificationPermissionCard()
        if (!vm.remindersOnTime) ExactAlarmCard()
        val t = today
        when {
            t == null -> CircularProgressIndicator()
            t.plan == null -> CheckInCard(checkedIn = t.checkedIn, onCheckIn = onCheckIn)
            else -> PlanSection(t.date, t.plan, t.day, profile, onLog = vm::log)
        }
    }
}

@Composable
private fun WindowLine(profile: LocalProfile, onEditSchedule: () -> Unit) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Text(
            "Training window ${profile.windowStart}–${profile.windowEnd}",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.weight(1f),
        )
        TextButton(onClick = onEditSchedule) { Text("Change") }
    }
}

@Composable
private fun ExactAlarmCard() {
    val context = LocalContext.current
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Get set reminders on time", style = MaterialTheme.typography.titleMedium)
            Text("Without Alarms & reminders, Android can hold a set reminder back by up to an hour.")
            Button(onClick = {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                    context.startActivity(
                        Intent(Settings.ACTION_REQUEST_SCHEDULE_EXACT_ALARM, Uri.parse("package:${context.packageName}"))
                    )
                }
            }) { Text("Allow on-time reminders") }
        }
    }
}

@Composable
private fun NotificationPermissionCard() {
    if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) return
    val context = LocalContext.current
    fun check() = ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) ==
        PackageManager.PERMISSION_GRANTED
    var granted by remember { mutableStateOf(check()) }
    // Also re-check on return, in case it was turned on in Settings.
    LifecycleEventEffect(Lifecycle.Event.ON_RESUME) { granted = check() }
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
private fun PlanSection(
    date: String,
    plan: PlanEntity,
    day: DayState?,
    profile: LocalProfile?,
    onLog: (String, String, Rating) -> Unit,
) {
    Text(plan.reason, style = MaterialTheme.typography.bodyLarge)
    if (plan.source == "fallback") Banner("Offline plan. It syncs when you're back online.")
    if (plan.kind == "mobility") {
        Banner("Rest day: gentle mobility only.")
        return
    }
    if (plan.kind == "window_passed") {
        val window = profile?.let { " (${it.windowStart}–${it.windowEnd})" } ?: ""
        val reminder = profile?.let {
            " Tomorrow's check-in reminder comes at ${Hhmm.format((Hhmm.toMinutes(it.wakeTime) + 15) % Hhmm.MINUTES_PER_DAY)}."
        } ?: ""
        Banner("You checked in after your training window$window, so there are no sets today.$reminder If your days look different, tap Change above.")
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
