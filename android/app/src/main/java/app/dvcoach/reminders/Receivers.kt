package app.dvcoach.reminders

import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.net.Uri
import app.dvcoach.DvCoachApp
import app.dvcoach.data.Repository
import app.dvcoach.engine.Rating
import kotlinx.coroutines.launch

/** Runs [block] off the main thread while keeping the broadcast alive until it finishes. */
private fun BroadcastReceiver.runAsync(context: Context, block: suspend (Repository) -> Unit) {
    val container = (context.applicationContext as DvCoachApp).container
    val pending = goAsync()
    container.scope.launch {
        try {
            block(container.repository)
        } finally {
            pending.finish()
        }
    }
}

private const val EXTRA_DATE = "date"
private const val EXTRA_REF = "ref"
private const val EXTRA_RATING = "rating"
private const val FLAGS = PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE

/** Fires when a set or the morning check-in is due. */
class AlarmReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        when (intent.action) {
            ACTION_SET_PROMPT -> {
                val date = intent.getStringExtra(EXTRA_DATE) ?: return
                val ref = intent.getStringExtra(EXTRA_REF) ?: return
                runAsync(context) { it.onPromptDue(date, ref) }
            }
            ACTION_CHECKIN_REMINDER -> runAsync(context) { it.onCheckinReminderDue() }
        }
    }

    companion object {
        private const val ACTION_SET_PROMPT = "app.dvcoach.action.SET_PROMPT"
        private const val ACTION_CHECKIN_REMINDER = "app.dvcoach.action.CHECKIN_REMINDER"

        // The data URI makes each set's PendingIntent distinct, so it can be replaced or cancelled alone.
        private fun setIntent(context: Context, ref: String) =
            Intent(context, AlarmReceiver::class.java)
                .setAction(ACTION_SET_PROMPT)
                .setData(Uri.parse("dvcoach://set/$ref"))

        fun setPrompt(context: Context, date: String, ref: String): PendingIntent =
            PendingIntent.getBroadcast(
                context, 0, setIntent(context, ref).putExtra(EXTRA_DATE, date).putExtra(EXTRA_REF, ref), FLAGS,
            )

        fun existingSetPrompt(context: Context, ref: String): PendingIntent? =
            PendingIntent.getBroadcast(
                context, 0, setIntent(context, ref), PendingIntent.FLAG_NO_CREATE or PendingIntent.FLAG_IMMUTABLE,
            )

        fun checkinReminder(context: Context): PendingIntent =
            PendingIntent.getBroadcast(
                context, 0, Intent(context, AlarmReceiver::class.java).setAction(ACTION_CHECKIN_REMINDER), FLAGS,
            )
    }
}

/** Notification buttons: Done, Hard and Snooze. Logging works with the app closed and offline. */
class LogActionReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val date = intent.getStringExtra(EXTRA_DATE) ?: return
        val ref = intent.getStringExtra(EXTRA_REF) ?: return
        when (intent.action) {
            ACTION_LOG -> {
                val rating = intent.getStringExtra(EXTRA_RATING)?.let { Rating.fromWire(it) } ?: return
                runAsync(context) { it.logSet(date, ref, rating) }
            }
            ACTION_SNOOZE -> runAsync(context) { it.snooze(date, ref) }
        }
    }

    companion object {
        private const val ACTION_LOG = "app.dvcoach.action.LOG"
        private const val ACTION_SNOOZE = "app.dvcoach.action.SNOOZE"

        fun log(context: Context, date: String, ref: String, rating: Rating): PendingIntent =
            PendingIntent.getBroadcast(
                context,
                0,
                Intent(context, LogActionReceiver::class.java)
                    .setAction(ACTION_LOG)
                    .setData(Uri.parse("dvcoach://log/$ref/${rating.wire}"))
                    .putExtra(EXTRA_DATE, date)
                    .putExtra(EXTRA_REF, ref)
                    .putExtra(EXTRA_RATING, rating.wire),
                FLAGS,
            )

        fun snooze(context: Context, date: String, ref: String): PendingIntent =
            PendingIntent.getBroadcast(
                context,
                0,
                Intent(context, LogActionReceiver::class.java)
                    .setAction(ACTION_SNOOZE)
                    .setData(Uri.parse("dvcoach://snooze/$ref"))
                    .putExtra(EXTRA_DATE, date)
                    .putExtra(EXTRA_REF, ref),
                FLAGS,
            )
    }
}

/** Alarms don't survive a reboot, and clock or time-zone changes move them. Re-register. */
class RescheduleReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action in HANDLED) runAsync(context) { it.rescheduleAll() }
    }

    private companion object {
        val HANDLED = setOf(
            Intent.ACTION_BOOT_COMPLETED,
            Intent.ACTION_TIME_CHANGED,
            Intent.ACTION_TIMEZONE_CHANGED,
            Intent.ACTION_MY_PACKAGE_REPLACED,
        )
    }
}
