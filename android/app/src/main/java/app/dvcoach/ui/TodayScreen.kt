package app.dvcoach.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.State
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import app.dvcoach.core.Hhmm
import app.dvcoach.data.Repository
import app.dvcoach.data.Repository.DayMark
import app.dvcoach.data.local.LocalProfile
import app.dvcoach.data.local.PlanEntity
import app.dvcoach.engine.DayState
import app.dvcoach.engine.DayStatus
import app.dvcoach.engine.Rating
import app.dvcoach.engine.SetState
import app.dvcoach.engine.SetStatus
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import java.time.LocalTime
import java.time.format.TextStyle
import java.util.Locale

/** A set's buttons unlock this many minutes before it's due. */
private const val EARLY_WINDOW_MIN = 10

class TodayViewModel(private val repository: Repository) : ViewModel() {
    val today: StateFlow<Repository.Today?> =
        repository.observeToday().stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), null)

    val profile: StateFlow<LocalProfile?> =
        repository.profile.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), null)

    val week: StateFlow<List<Repository.WeekDay>> =
        repository.observeWeek().stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    fun log(date: String, ref: String, rating: Rating, doneReps: Int?) {
        viewModelScope.launch { repository.logSet(date, ref, rating, doneReps) }
    }
}

@Composable
fun TodayScreen(repository: Repository, onCheckIn: () -> Unit, onEditSchedule: () -> Unit) {
    val vm = repoViewModel(repository) { TodayViewModel(it) }
    val today by vm.today.collectAsStateWithLifecycle()
    val profile by vm.profile.collectAsStateWithLifecycle()
    val week by vm.week.collectAsStateWithLifecycle()
    val reminders = rememberReminderState(repository)
    val now by rememberMinuteClock()
    var showGuide by remember { mutableStateOf(false) }

    ScreenColumn {
        Text("Today", style = MaterialTheme.typography.headlineMedium)
        WeekStrip(week)
        profile?.let { WindowLine(it, onEditSchedule) }
        ReminderCards(reminders)
        val t = today
        when {
            t == null -> CircularProgressIndicator()
            t.plan == null -> CheckInHero(checkedIn = t.checkedIn, onCheckIn = onCheckIn)
            else -> PlanSection(t.date, t.plan, t.day, profile, now, onLog = vm::log, onShowGuide = { showGuide = true })
        }
    }
    if (showGuide) PushupGuideSheet(onDismiss = { showGuide = false })
}

/** The current time, refreshed every 30 seconds, for "in 25 min" and unlocking the next set. */
@Composable
private fun rememberMinuteClock(): State<LocalTime> = produceState(LocalTime.now()) {
    while (true) {
        delay(30_000)
        value = LocalTime.now()
    }
}

@Composable
private fun WeekStrip(days: List<Repository.WeekDay>) {
    if (days.isEmpty()) return
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        days.forEachIndexed { i, day -> DayDot(day, isToday = i == days.lastIndex) }
    }
}

@Composable
private fun DayDot(day: Repository.WeekDay, isToday: Boolean) {
    val colors = MaterialTheme.colorScheme
    val fill = when (day.mark) {
        DayMark.TRAINED -> colors.primary
        DayMark.REST -> colors.secondaryContainer
        else -> Color.Transparent
    }
    val content = when (day.mark) {
        DayMark.TRAINED -> colors.onPrimary
        DayMark.REST -> colors.onSecondaryContainer
        DayMark.CHECKED_IN -> colors.onSurface
        DayMark.NONE -> colors.onSurfaceVariant
    }
    val ring = when {
        day.mark == DayMark.CHECKED_IN -> colors.outline
        isToday && day.mark == DayMark.NONE -> colors.primary
        else -> null
    }
    val weekday = day.date.dayOfWeek.getDisplayName(TextStyle.SHORT, Locale.getDefault())
    val meaning = when (day.mark) {
        DayMark.TRAINED -> "trained"
        DayMark.REST -> "rest day"
        DayMark.CHECKED_IN -> "checked in, no sets"
        DayMark.NONE -> "nothing logged"
    }
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(4.dp),
        modifier = Modifier.semantics(mergeDescendants = true) {
            contentDescription = "$weekday ${day.date.dayOfMonth}: $meaning"
        },
    ) {
        Text(
            day.date.dayOfWeek.getDisplayName(TextStyle.NARROW, Locale.getDefault()),
            style = MaterialTheme.typography.labelSmall,
            color = colors.onSurfaceVariant,
        )
        Box(
            modifier = Modifier
                .size(36.dp)
                .clip(CircleShape)
                .background(fill)
                .then(if (ring != null) Modifier.border(1.5.dp, ring, CircleShape) else Modifier),
            contentAlignment = Alignment.Center,
        ) {
            Text(
                if (day.mark == DayMark.TRAINED) "✓" else "${day.date.dayOfMonth}",
                color = content,
                style = MaterialTheme.typography.labelLarge,
            )
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
private fun HeroCard(error: Boolean = false, content: @Composable () -> Unit) {
    val colors = MaterialTheme.colorScheme
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = if (error) colors.errorContainer else colors.primaryContainer,
            contentColor = if (error) colors.onErrorContainer else colors.onPrimaryContainer,
        ),
    ) {
        Column(modifier = Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) { content() }
    }
}

@Composable
private fun Eyebrow(text: String) {
    Text(text.uppercase(), style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.SemiBold)
}

@Composable
private fun CheckInHero(checkedIn: Boolean, onCheckIn: () -> Unit) {
    HeroCard {
        Eyebrow("Morning check-in")
        Text(
            if (checkedIn) "The plan didn't arrive" else "How are you today?",
            style = MaterialTheme.typography.headlineSmall,
        )
        Text(
            if (checkedIn) "Your answers are saved. Try again when you have a connection."
            else "Three quick questions, then today's sets.",
        )
        Button(onClick = onCheckIn, modifier = Modifier.fillMaxWidth()) {
            Text(if (checkedIn) "Try again" else "Check in")
        }
    }
}

@Composable
private fun PlanSection(
    date: String,
    plan: PlanEntity,
    day: DayState?,
    profile: LocalProfile?,
    now: LocalTime,
    onLog: (String, String, Rating, Int?) -> Unit,
    onShowGuide: () -> Unit,
) {
    when {
        plan.kind == "mobility" -> HeroCard {
            Eyebrow("Rest day")
            Text("No push-ups today", style = MaterialTheme.typography.headlineSmall)
            Text("Gentle mobility only. A planned rest day counts towards your week.")
        }
        plan.kind == "window_passed" -> HeroCard {
            val window = profile?.let { " (${it.windowStart}–${it.windowEnd})" } ?: ""
            val reminder = profile?.let {
                " Tomorrow's check-in reminder comes at ${Hhmm.format((Hhmm.toMinutes(it.wakeTime) + 15) % Hhmm.MINUTES_PER_DAY)}."
            } ?: ""
            Eyebrow("No sets today")
            Text("Your training window has ended", style = MaterialTheme.typography.headlineSmall)
            Text("You checked in after your window$window.$reminder If your days look different, tap Change above.")
        }
        day != null && day.sets.isNotEmpty() -> SetHero(date, day, now, onLog, onShowGuide)
    }
    if (plan.source == "fallback") Banner("Offline plan. It syncs when you're back online.")
    Text(plan.reason, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)

    if (day == null || day.sets.isEmpty()) return
    val next = if (day.status == DayStatus.ACTIVE) day.nextPending else null
    Text("Today's sets", style = MaterialTheme.typography.titleMedium)
    Column {
        day.sets.forEach { SetRow(it, isNext = it.ref == next?.ref) }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun SetHero(
    date: String,
    day: DayState,
    now: LocalTime,
    onLog: (String, String, Rating, Int?) -> Unit,
    onShowGuide: () -> Unit,
) {
    val next = if (day.status == DayStatus.ACTIVE) day.nextPending else null
    val total = day.sets.count { it.status != SetStatus.DROPPED }
    val done = day.sets.count { it.status == SetStatus.LOGGED && it.rating !in setOf(Rating.SKIPPED, Rating.PAIN) }
    var earlyAllowedFor by remember { mutableStateOf<String?>(null) }
    var confirmEarly by remember { mutableStateOf(false) }
    var painFor by remember { mutableStateOf<SetState?>(null) }

    HeroCard(error = day.status == DayStatus.STOPPED_PAIN) {
        when {
            next != null -> {
                val minutesUntil = Hhmm.toMinutes(next.at) - (now.hour * 60 + now.minute)
                val unlocked = minutesUntil <= EARLY_WINDOW_MIN || earlyAllowedFor == next.ref
                Eyebrow("Next set")
                Text("${next.targetReps} push-ups", style = MaterialTheme.typography.displaySmall, fontWeight = FontWeight.Bold)
                Text(
                    when {
                        minutesUntil > 0 -> "at ${next.at} · in ${formatMinutes(minutesUntil)}"
                        minutesUntil == 0 -> "due now"
                        else -> "due since ${next.at}"
                    },
                    style = MaterialTheme.typography.titleMedium,
                )
                if (unlocked) {
                    Text("Stop with a few reps left in the tank. Hard means only 0–1 were left.", style = MaterialTheme.typography.bodySmall)
                    FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { onLog(date, next.ref, Rating.SOLID, null) }) { Text("Done") }
                        FilledTonalButton(onClick = { onLog(date, next.ref, Rating.EASY, null) }) { Text("Easy") }
                        FilledTonalButton(onClick = { onLog(date, next.ref, Rating.HARD, null) }) { Text("Hard") }
                        OutlinedButton(onClick = { painFor = next }) { Text("Pain") }
                        TextButton(onClick = { onLog(date, next.ref, Rating.SKIPPED, null) }) { Text("Skip") }
                    }
                } else {
                    Text("Sets work best spread out, with real rest in between. You'll get a reminder when it's due.")
                    TextButton(onClick = { confirmEarly = true }) { Text("Do it now anyway") }
                }
            }
            day.status == DayStatus.COMPLETE -> {
                Eyebrow("Today")
                Text("All done for today", style = MaterialTheme.typography.headlineSmall)
                Text("Nice work. See you tomorrow.")
            }
            day.status == DayStatus.ENDED_HARD -> {
                Eyebrow("Today")
                Text("That's enough for today", style = MaterialTheme.typography.headlineSmall)
                Text("Two hard sets mean you need rest more than reps. Come back tomorrow.")
            }
            day.status == DayStatus.STOPPED_PAIN -> {
                Eyebrow("Today")
                Text("Stopped for today", style = MaterialTheme.typography.headlineSmall)
                Text("Push-ups are off for the rest of the day because of pain. If it comes back, check with a professional.")
            }
            else -> {
                Eyebrow("Today")
                Text("No more sets today", style = MaterialTheme.typography.headlineSmall)
            }
        }
        if (total > 0) {
            LinearProgressIndicator(progress = { done.toFloat() / total }, modifier = Modifier.fillMaxWidth())
            Text("$done of $total sets done", style = MaterialTheme.typography.bodySmall)
        }
        TextButton(onClick = onShowGuide) { Text("How to do a push-up") }
    }

    if (confirmEarly && next != null) {
        AlertDialog(
            onDismissRequest = { confirmEarly = false },
            title = { Text("Do this set now?") },
            text = { Text("Doing it early means less rest since your last set, which is what makes spread-out sets work.") },
            confirmButton = {
                TextButton(onClick = {
                    earlyAllowedFor = next.ref
                    confirmEarly = false
                }) { Text("Do it now") }
            },
            dismissButton = { TextButton(onClick = { confirmEarly = false }) { Text("Wait") } },
        )
    }
    painFor?.let { set ->
        PainDialog(
            target = set.targetReps,
            onConfirm = { reps ->
                onLog(date, set.ref, Rating.PAIN, reps)
                painFor = null
            },
            onDismiss = { painFor = null },
        )
    }
}

@Composable
private fun PainDialog(target: Int, onConfirm: (Int) -> Unit, onDismiss: () -> Unit) {
    var reps by remember { mutableStateOf("0") }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Stop push-ups for today?") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text("How many did you do before it hurt? The rest of today's sets will be dropped.")
                NumberField("Reps done (of $target)", reps, { reps = it })
            }
        },
        confirmButton = {
            TextButton(onClick = { onConfirm((reps.toIntOrNull() ?: 0).coerceIn(0, 500)) }) { Text("Stop for today") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } },
    )
}

private fun formatMinutes(minutes: Int): String =
    if (minutes < 60) "$minutes min" else "${minutes / 60} h ${minutes % 60} min"

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
