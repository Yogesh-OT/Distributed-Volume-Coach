package app.dvcoach.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.ButtonDefaults
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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import app.dvcoach.BuildConfig
import app.dvcoach.data.Repository
import app.dvcoach.data.local.LocalProfile
import app.dvcoach.data.remote.ApiResult
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

class SettingsViewModel(private val repository: Repository) : ViewModel() {
    val profile: StateFlow<LocalProfile?> =
        repository.profile.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), null)

    var deleteError by mutableStateOf<String?>(null)
        private set
    var resetMessage by mutableStateOf<String?>(null)
        private set

    /** On success the cleared profile sends the app back to onboarding. */
    fun deleteAccount() {
        viewModelScope.launch {
            val result = repository.deleteAccount()
            if (result is ApiResult.Failed) deleteError = result.message
        }
    }

    fun resetToday() {
        resetMessage = "Resetting…"
        viewModelScope.launch {
            resetMessage = when (val result = repository.resetToday()) {
                is ApiResult.Ok -> "Today is reset. Check in again from the Today tab."
                is ApiResult.Failed -> result.message
            }
        }
    }
}

@Composable
fun SettingsScreen(repository: Repository, onEditSchedule: () -> Unit, onEditWorkouts: () -> Unit = {}) {
    val vm = repoViewModel(repository) { SettingsViewModel(it) }
    val profile by vm.profile.collectAsStateWithLifecycle()
    val reminders = rememberReminderState(repository)
    val context = LocalContext.current
    var confirmDelete by remember { mutableStateOf(false) }

    ScreenColumn {
        Text("Settings", style = MaterialTheme.typography.headlineMedium)

        Section("Your day") {
            profile?.let {
                InfoRow("Wake up", it.wakeTime)
                InfoRow("Training window", "${it.windowStart}–${it.windowEnd}")
                InfoRow("Quiet hours", "${it.quietStart}–${it.quietEnd}")
                InfoRow("Prompts a day", "Up to ${it.promptLimit}")
            }
            OutlinedButton(onClick = onEditSchedule) { Text("Change your day") }
        }
        HorizontalDivider()

        Section("Workouts") {
            Text("Short sessions for building muscle or getting fit, planned around what you have at home.")
            OutlinedButton(onClick = onEditWorkouts) { Text("Set up workouts") }
        }
        HorizontalDivider()

        Section("Reminders") {
            StatusRow(
                label = "Notifications",
                ok = reminders.notifications,
                detail = if (reminders.notifications) "On" else "Off. Set reminders won't show.",
                action = "Allow",
                onAction = reminders.requestNotifications,
            )
            StatusRow(
                label = "On-time reminders",
                ok = reminders.onTime,
                detail = if (reminders.onTime) "On" else "Off. Reminders can be up to an hour late.",
                action = "Allow",
                onAction = reminders.openAlarmSettings,
            )
            if (isXiaomiFamily()) {
                Text(
                    "On Xiaomi, Redmi and POCO phones, also turn on Autostart and set Battery saver to No restrictions for DV Coach. Otherwise reminders can stop while the app is closed.",
                    style = MaterialTheme.typography.bodySmall,
                )
            }
            TextButton(onClick = { openAppSettings(context) }) { Text("Open app settings") }
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

        if (repository.server.isEditable) {
            HorizontalDivider()
            Section("Test tools") {
                Text(
                    "Reset today forgets today's check-in, plan and logged sets on this phone and the server, so you can check in again.",
                    style = MaterialTheme.typography.bodySmall,
                )
                OutlinedButton(onClick = vm::resetToday) { Text("Reset today") }
                vm.resetMessage?.let { Text(it, style = MaterialTheme.typography.bodySmall) }
            }
            ServerAddressCard(repository)
        }

        Text(
            "DV Coach ${BuildConfig.VERSION_NAME}",
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
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
private fun InfoRow(label: String, value: String) {
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(value)
    }
}

@Composable
private fun StatusRow(label: String, ok: Boolean, detail: String, action: String, onAction: () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(label)
            Text(
                detail,
                style = MaterialTheme.typography.bodySmall,
                color = if (ok) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error,
            )
        }
        if (!ok) TextButton(onClick = onAction) { Text(action) }
    }
}
