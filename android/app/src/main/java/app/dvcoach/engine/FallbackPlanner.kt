package app.dvcoach.engine

import app.dvcoach.core.Hhmm
import kotlin.math.floor
import kotlin.math.max
import kotlin.math.min

/**
 * Builds a cautious plan when the server can't be reached at check-in:
 * the last plan's reps, one set fewer, spread evenly over what's left of the window.
 */
object FallbackPlanner {
    const val CHECKIN_LEAD_MIN = 15
    const val ENGINE_VERSION = "phone-0.1.0"

    data class Result(val sets: List<PlannedSet>, val policy: Policy, val reason: String)

    fun build(
        lastSets: List<PlannedSet>,
        lastPolicy: Policy,
        windowStart: String,
        windowEnd: String,
        checkinTime: String,
    ): Result? {
        if (lastSets.isEmpty()) return null
        val policy = lastPolicy.copy(windowEnd = windowEnd)
        val reps = lastSets.first().targetReps
        val wanted = max(1, lastSets.size - 1)

        val end = Hhmm.toMinutes(windowEnd)
        val start = max(Hhmm.toMinutes(windowStart), Hhmm.toMinutes(checkinTime) + CHECKIN_LEAD_MIN)
        val available = end - start
        if (available < 0) {
            return Result(emptyList(), policy, "Your training window has ended for today. See you tomorrow.")
        }

        val count = min(wanted, max(1, available / policy.minGapMin))
        val segment = available.toDouble() / count
        val sets = (0 until count).map { i ->
            val at = start + floor(i * segment + segment / 2).toInt()
            PlannedSet(ref = "s${i + 1}", at = Hhmm.format(at), targetReps = reps)
        }
        return Result(
            sets,
            policy,
            "Offline plan: $count sets of $reps, one fewer than your last plan. It syncs when you're back online.",
        )
    }
}
