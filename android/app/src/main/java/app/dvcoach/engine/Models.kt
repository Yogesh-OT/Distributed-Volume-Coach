package app.dvcoach.engine

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class PlannedSet(
    val ref: String,
    val at: String,
    @SerialName("target_reps") val targetReps: Int,
)

@Serializable
data class OnHard(
    @SerialName("scale_remaining_reps") val scaleRemainingReps: Double,
    @SerialName("delay_remaining_min") val delayRemainingMin: Int,
)

/** In-day rules, sent by the server inside every plan. */
@Serializable
data class Policy(
    @SerialName("on_hard") val onHard: OnHard,
    @SerialName("end_day_after_hard_sets") val endDayAfterHardSets: Int,
    @SerialName("on_pain") val onPain: String = "stop_exercise_today",
    @SerialName("min_gap_min") val minGapMin: Int,
    @SerialName("window_end") val windowEnd: String,
    @SerialName("quiet_hours") val quietHours: List<String>,
)

enum class Rating {
    EASY, SOLID, HARD, PAIN, SKIPPED;

    val wire: String get() = name.lowercase()

    companion object {
        fun fromWire(value: String): Rating = valueOf(value.uppercase())
    }
}

enum class SetStatus { LOGGED, MISSED, PENDING, DROPPED }

enum class DayStatus { ACTIVE, COMPLETE, ENDED_HARD, STOPPED_PAIN }

data class LoggedSet(val ref: String, val rating: Rating, val at: String)

data class SetState(
    val ref: String,
    val at: String,
    val targetReps: Int,
    val status: SetStatus,
    val rating: Rating? = null,
)

data class DayState(val sets: List<SetState>, val status: DayStatus, val hardSets: Int) {
    val nextPending: SetState? get() = sets.firstOrNull { it.status == SetStatus.PENDING }
}
