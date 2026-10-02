package app.dvcoach.core

import java.time.LocalTime
import java.util.Locale
import kotlin.math.floor

/** Local wall-clock times as "HH:MM", the format the server and the plan use. */
object Hhmm {
    const val MINUTES_PER_DAY = 24 * 60

    fun toMinutes(hhmm: String): Int {
        val parts = hhmm.split(":")
        require(parts.size == 2) { "expected HH:MM, got $hhmm" }
        val h = parts[0].toInt()
        val m = parts[1].toInt()
        require(h in 0..23 && m in 0..59) { "time out of range: $hhmm" }
        return h * 60 + m
    }

    // Locale.ROOT keeps ASCII digits on devices set to languages with other numerals.
    fun format(minutes: Int): String {
        require(minutes in 0 until MINUTES_PER_DAY) { "minutes out of range: $minutes" }
        return String.format(Locale.ROOT, "%02d:%02d", minutes / 60, minutes % 60)
    }

    fun of(time: LocalTime): String = format(time.hour * 60 + time.minute)

    fun toLocalTime(hhmm: String): LocalTime = LocalTime.of(toMinutes(hhmm) / 60, toMinutes(hhmm) % 60)
}

/** Halves round up, matching the server's round_half_up(). */
fun roundHalfUp(x: Double): Int = floor(x + 0.5 + 1e-9).toInt()
