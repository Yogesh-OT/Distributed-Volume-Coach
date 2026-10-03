package app.dvcoach.reminders

import android.app.AlarmManager
import android.app.PendingIntent
import android.content.Context
import android.os.Build
import app.dvcoach.core.Hhmm
import app.dvcoach.engine.SetState
import java.time.Clock
import java.time.Instant
import java.time.LocalDate

/**
 * Exact alarms when the user has allowed "Alarms & reminders", otherwise inexact ones.
 * Inexact alarms need no permission but Android may deliver them up to an hour late
 * (seen on a Xiaomi running Android API 36). Both kinds still fire in Doze.
 */
class PromptScheduler(private val context: Context, private val clock: Clock = Clock.systemDefaultZone()) {
    private val alarms: AlarmManager = context.getSystemService(AlarmManager::class.java)

    /** Below Android 12 exact alarms need no permission. */
    fun canScheduleExact(): Boolean =
        Build.VERSION.SDK_INT < Build.VERSION_CODES.S || alarms.canScheduleExactAlarms()

    fun scheduleSets(date: LocalDate, pending: List<SetState>) {
        cancelSets()
        val now = Instant.now(clock)
        for (set in pending) {
            val trigger = date.atTime(Hhmm.toLocalTime(set.at)).atZone(clock.zone).toInstant()
            if (trigger.isAfter(now)) {
                schedule(trigger.toEpochMilli(), AlarmReceiver.setPrompt(context, date.toString(), set.ref))
            }
        }
    }

    fun scheduleCheckinReminder(wakeTime: String, checkedInToday: Boolean) {
        var at = LocalDate.now(clock).atTime(Hhmm.toLocalTime(wakeTime).plusMinutes(CHECKIN_AFTER_WAKE_MIN)).atZone(clock.zone)
        if (checkedInToday || !at.toInstant().isAfter(Instant.now(clock))) at = at.plusDays(1)
        schedule(at.toInstant().toEpochMilli(), AlarmReceiver.checkinReminder(context))
    }

    fun cancelAll() {
        cancelSets()
        alarms.cancel(AlarmReceiver.checkinReminder(context))
    }

    fun cancelSets() {
        for (i in 1..MAX_SETS) {
            AlarmReceiver.existingSetPrompt(context, "s$i")?.let { alarms.cancel(it) }
        }
    }

    private fun schedule(triggerAtMillis: Long, operation: PendingIntent) {
        if (canScheduleExact()) {
            try {
                alarms.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, triggerAtMillis, operation)
                return
            } catch (e: SecurityException) {
                // Permission revoked between the check and the call: fall through to inexact.
            }
        }
        alarms.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, triggerAtMillis, operation)
    }

    companion object {
        const val MAX_SETS = 16
        const val CHECKIN_AFTER_WAKE_MIN = 15L
    }
}
