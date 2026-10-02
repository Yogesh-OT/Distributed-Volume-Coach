package app.dvcoach.engine

import app.dvcoach.core.Hhmm
import app.dvcoach.core.roundHalfUp
import kotlin.math.max
import kotlin.math.min

/**
 * Port of server/engine/policy.py: how logged sets change the rest of today.
 * Both versions run every case in shared/policy_vectors.json.
 */
object InDayPolicy {

    private class Working(
        val ref: String,
        var at: Int,
        var target: Int,
        var status: SetStatus = SetStatus.PENDING,
        var rating: Rating? = null,
    )

    fun apply(sets: List<PlannedSet>, policy: Policy, logs: List<LoggedSet>): DayState {
        val work = sets.map { Working(it.ref, Hhmm.toMinutes(it.at), it.targetReps) }
        val index = work.withIndex().associate { it.value.ref to it.index }
        val windowEnd = Hhmm.toMinutes(policy.windowEnd)
        var status = DayStatus.ACTIVE
        var hard = 0

        // sortedBy is stable: logs at the same minute keep their order.
        for (log in logs.sortedBy { Hhmm.toMinutes(it.at) }) {
            val i = index[log.ref] ?: continue
            if (status != DayStatus.ACTIVE || work[i].status != SetStatus.PENDING) continue

            work[i].status = SetStatus.LOGGED
            work[i].rating = log.rating
            for (j in 0 until i) {
                if (work[j].status == SetStatus.PENDING) work[j].status = SetStatus.MISSED
            }
            val remaining = work.drop(i + 1).filter { it.status == SetStatus.PENDING }

            if (log.rating == Rating.PAIN) {
                status = DayStatus.STOPPED_PAIN
                remaining.forEach { it.status = SetStatus.DROPPED }
                continue
            }
            if (log.rating == Rating.HARD) {
                hard++
                if (hard >= policy.endDayAfterHardSets) {
                    status = DayStatus.ENDED_HARD
                    remaining.forEach { it.status = SetStatus.DROPPED }
                    continue
                }
                for (w in remaining) {
                    w.target = max(1, roundHalfUp(w.target * policy.onHard.scaleRemainingReps))
                    w.at += policy.onHard.delayRemainingMin
                }
            }

            var previous = Hhmm.toMinutes(log.at)
            for (w in remaining) {
                w.at = max(w.at, previous + policy.minGapMin)
                previous = w.at
                if (w.at > windowEnd) w.status = SetStatus.DROPPED
            }
        }

        if (status == DayStatus.ACTIVE && work.none { it.status == SetStatus.PENDING } && logs.isNotEmpty()) {
            status = DayStatus.COMPLETE
        }

        return DayState(
            sets = work.map {
                // Sets pushed past midnight are already dropped; clamp so they still format.
                SetState(it.ref, Hhmm.format(min(it.at, Hhmm.MINUTES_PER_DAY - 1)), it.target, it.status, it.rating)
            },
            status = status,
            hardSets = hard,
        )
    }
}
