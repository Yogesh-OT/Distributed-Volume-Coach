package app.dvcoach.reminders

import android.app.AlarmManager
import android.content.Context
import app.dvcoach.core.Hhmm
import app.dvcoach.engine.SetState
import java.time.Clock
import java.time.Instant
import java.time.LocalDate

/**
 * Inexact alarms only. setAndAllowWhileIdle still fires in Doze, may arrive a few minutes
 * late, and needs no special permission. Spread-out practice doesn't need exact times.
 */
class PromptScheduler(private val context: Context, private val clock: Clock = Clock.systemDefaultZone()) {
    private val alarms: AlarmManager = context.getSystemService(AlarmManager::class.java)

    fun scheduleSets(date: LocalDate, pending: List<SetState>) {
        cancelSets()
        val now = Instant.now(clock)
        for (set in pending) {
            val trigger = date.atTime(Hhmm.toLocalTime(set.at)).atZone(clock.zone).toInstant()
            if (trigger.isAfter(now)) {
                alarms.setAndAllowWhileIdle(
                    AlarmManager.RTC_WAKEUP,
                    trigger.toEpochMilli(),
                    AlarmReceiver.setPrompt(context, date.toString(), set.ref),
                )
            }
        }
    }

    fun scheduleCheckinReminder(wakeTime: String, checkedInToday: Boolean) {
        var at = LocalDate.now(clock).atTime(Hhmm.toLocalTime(wakeTime).plusMinutes(CHECKIN_AFTER_WAKE_MIN)).atZone(clock.zone)
        if (checkedInToday || !at.toInstant().isAfter(Instant.now(clock))) at = at.plusDays(1)
        alarms.setAndAllowWhileIdle(
            AlarmManager.RTC_WAKEUP,
            at.toInstant().toEpochMilli(),
            AlarmReceiver.checkinReminder(context),
        )
    }

    fun cancelAll() {
        cancelSets()
        alarms.cancel(AlarmReceiver.checkinReminder(context))
    }

    private fun cancelSets() {
        for (i in 1..MAX_SETS) {
            AlarmReceiver.existingSetPrompt(context, "s$i")?.let { alarms.cancel(it) }
        }
    }

    companion object {
        const val MAX_SETS = 16
        const val CHECKIN_AFTER_WAKE_MIN = 15L
    }
}
