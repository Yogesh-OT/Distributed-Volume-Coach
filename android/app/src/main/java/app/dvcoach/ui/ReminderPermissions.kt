package app.dvcoach.ui

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.provider.Settings
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LifecycleEventEffect
import app.dvcoach.data.Repository
import kotlinx.coroutines.launch

fun notificationsAllowed(context: Context): Boolean =
    Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU ||
        ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) ==
        PackageManager.PERMISSION_GRANTED

fun openAppSettings(context: Context) {
    context.startActivity(
        Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:${context.packageName}"))
    )
}

/** Xiaomi, Redmi and POCO phones stop background apps unless Autostart is on. */
fun isXiaomiFamily(): Boolean = Build.MANUFACTURER.lowercase() in setOf("xiaomi", "redmi", "poco")

class ReminderState(
    val notifications: Boolean,
    val onTime: Boolean,
    val requestNotifications: () -> Unit,
    val openAlarmSettings: () -> Unit,
)

/**
 * Notification and "Alarms & reminders" status, re-read whenever the screen comes back
 * into view (for example from a Settings page). Granting on-time reminders re-registers
 * today's alarms so they become exact.
 */
@Composable
fun rememberReminderState(repository: Repository): ReminderState {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var notifications by remember { mutableStateOf(notificationsAllowed(context)) }
    var onTime by remember { mutableStateOf(repository.remindersOnTime()) }
    LifecycleEventEffect(Lifecycle.Event.ON_RESUME) {
        notifications = notificationsAllowed(context)
        val nowOnTime = repository.remindersOnTime()
        if (nowOnTime && !onTime) scope.launch { repository.rescheduleAll() }
        onTime = nowOnTime
    }
    // After two refusals Android stops showing the prompt; the Settings tab links to app settings for that case.
    val launcher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { notifications = it }
    return ReminderState(
        notifications = notifications,
        onTime = onTime,
        requestNotifications = {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                launcher.launch(Manifest.permission.POST_NOTIFICATIONS)
            }
        },
        openAlarmSettings = {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                context.startActivity(
                    Intent(Settings.ACTION_REQUEST_SCHEDULE_EXACT_ALARM, Uri.parse("package:${context.packageName}"))
                )
            }
        },
    )
}

/** Shown on Today only while something needs fixing. */
@Composable
fun ReminderCards(state: ReminderState) {
    if (!state.notifications) {
        PermissionCard(
            title = "Turn on notifications",
            body = "Each set arrives as a notification you can log from. Without them, you'd need to open the app to see when the next set is due.",
            action = "Allow notifications",
            onClick = state.requestNotifications,
        )
    }
    if (!state.onTime) {
        PermissionCard(
            title = "Get set reminders on time",
            body = "Without Alarms & reminders, Android can hold a set reminder back by up to an hour.",
            action = "Allow on-time reminders",
            onClick = state.openAlarmSettings,
        )
    }
}

@Composable
private fun PermissionCard(title: String, body: String, action: String, onClick: () -> Unit) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(title, style = MaterialTheme.typography.titleMedium)
            Text(body)
            Button(onClick = onClick) { Text(action) }
        }
    }
}
