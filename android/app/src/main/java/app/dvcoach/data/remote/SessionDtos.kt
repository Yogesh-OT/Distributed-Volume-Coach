package app.dvcoach.data.remote

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// Session mode. Field names follow server/app/schemas.py and server/app/routers/sessions.py.
// shared/session_samples.json holds real server responses; SessionDtosTest decodes them.

@Serializable
data class SessionSettingsDto(
    val mode: String = "sessions",
    val goal: String,
    @SerialName("days_per_week") val daysPerWeek: Int,
    @SerialName("session_minutes") val sessionMinutes: Int,
    val weekdays: List<Int> = emptyList(),
    /** Null lets the server assume a wall, a chair, a doorway and a smooth floor. */
    val available: List<String>? = null,
    @SerialName("high_impact") val highImpact: Boolean = false,
)

@Serializable
data class ExerciseStateDto(
    val ladder: String,
    val title: String,
    val level: Int,
    val name: String,
    val target: Int,
    val unit: String,
    @SerialName("rep_range") val repRange: List<Int>,
    @SerialName("each_side") val eachSide: Boolean,
    val paused: Boolean,
)

@Serializable
data class ExerciseStateChangeDto(val level: Int? = null, val paused: Boolean? = null)

@Serializable
data class SessionStartDto(
    val date: String,
    @SerialName("sleep_quality") val sleepQuality: Int? = null,
    val soreness: Int? = null,
    val energy: Int? = null,
)

@Serializable
data class PlannedExerciseDto(
    val ladder: String,
    val key: String,
    val name: String,
    val level: Int,
    val sets: Int,
    val target: Int,
    val unit: String,
    @SerialName("each_side") val eachSide: Boolean,
    @SerialName("rep_range") val repRange: List<Int>,
    @SerialName("test_last_set") val testLastSet: Boolean,
    @SerialName("rest_s") val restSeconds: Int,
    val cue: String,
)

@Serializable
data class CircuitDto(
    val level: Int,
    @SerialName("work_s") val workSeconds: Int,
    @SerialName("rest_s") val restSeconds: Int,
    val rounds: Int,
    val moves: List<String>,
)

@Serializable
data class SessionPayloadDto(
    val template: String,
    val title: String,
    val goal: String,
    val pairs: List<List<PlannedExerciseDto>>,
    val circuit: CircuitDto? = null,
    @SerialName("warmup_s") val warmupSeconds: Int,
    val minutes: Int,
    val light: Boolean,
    val note: String,
    @SerialName("total_sets") val totalSets: Int,
    val notes: List<String> = emptyList(),
)

@Serializable
data class StepDto(val ladder: String, val decision: String, val note: String)

@Serializable
data class SessionSummaryDto(
    val date: String,
    val finished: Boolean,
    @SerialName("sets_done") val setsDone: Int,
    val steps: List<StepDto>,
    @SerialName("circuit_note") val circuitNote: String? = null,
)

@Serializable
data class SessionDto(
    val date: String,
    val template: String,
    val goal: String,
    val minutes: Int,
    @SerialName("volume_step") val volumeStep: Int,
    val readiness: Double? = null,
    val payload: SessionPayloadDto,
    @SerialName("engine_version") val engineVersion: String,
    @SerialName("completed_at") val completedAt: String? = null,
    val summary: SessionSummaryDto? = null,
)

@Serializable
data class SessionLogDto(
    /** Made on the phone, so a retried upload never counts a set twice. */
    val id: String,
    val date: String,
    val ladder: String,
    @SerialName("exercise_key") val exerciseKey: String,
    val level: Int,
    @SerialName("set_number") val setNumber: Int,
    val target: Int,
    val done: Int,
    val effort: String, // easy, good, hard, max
    val tested: Boolean = false,
    val pain: Boolean = false,
    @SerialName("logged_at") val loggedAt: String,
)

@Serializable
data class SessionLogBatchDto(val logs: List<SessionLogDto>)

@Serializable
data class SessionCompleteDto(
    val finished: Boolean,
    @SerialName("quit_reason") val quitReason: String? = null, // too_hard, dont_know_how, no_time, pain, just_looking
    @SerialName("circuit_rating") val circuitRating: String? = null, // easy, good, hard, too_hard
)

@Serializable
data class MuscleSetsDto(val muscle: String, val sets: Double)

@Serializable
data class WeekSummaryDto(@SerialName("week_start") val weekStart: String, val sessions: Int, val sets: Int)

@Serializable
data class ExerciseHistoryDto(val date: String, val level: Int, val best: Int)

@Serializable
data class ExerciseProgressDto(val state: ExerciseStateDto, val history: List<ExerciseHistoryDto>)

@Serializable
data class WaistDto(@SerialName("measured_on") val measuredOn: String, @SerialName("waist_cm") val waistCm: Double)

@Serializable
data class ReportDto(
    @SerialName("week_start") val weekStart: String,
    @SerialName("sessions_planned") val sessionsPlanned: Int,
    @SerialName("sessions_done") val sessionsDone: Int,
    @SerialName("sets_done") val setsDone: Int,
    val minutes: Int,
    @SerialName("week_streak") val weekStreak: Int,
    @SerialName("best_week_streak") val bestWeekStreak: Int,
    val muscles: List<MuscleSetsDto>,
    @SerialName("target_band") val targetBand: List<Int>,
    val weeks: List<WeekSummaryDto>,
    val exercises: List<ExerciseProgressDto>,
    val weights: List<WeightDto>,
    val waists: List<WaistDto>,
    @SerialName("weekly_weight_change_pct") val weeklyWeightChangePct: Double? = null,
)

@Serializable
data class LibraryExerciseDto(
    val key: String,
    val name: String,
    val level: Int,
    val cue: String,
    @SerialName("each_side") val eachSide: Boolean,
    val needs: List<String>,
    @SerialName("rep_range") val repRange: List<Int>,
    @SerialName("test_last_set") val testLastSet: Boolean,
)

@Serializable
data class LadderDto(
    val key: String,
    val title: String,
    val unit: String,
    @SerialName("rep_range") val repRange: List<Int>,
    val step: Int,
    val muscles: Map<String, Double>,
    val exercises: List<LibraryExerciseDto>,
)

@Serializable
data class CardioMoveDto(
    val key: String,
    @SerialName("low_impact") val lowImpact: String,
    @SerialName("high_impact") val highImpact: String,
    val cue: String,
)

@Serializable
data class LibraryDto(
    val ladders: List<LadderDto>,
    @SerialName("cardio_moves") val cardioMoves: List<CardioMoveDto>,
)
