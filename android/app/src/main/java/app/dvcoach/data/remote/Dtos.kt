package app.dvcoach.data.remote

import app.dvcoach.engine.PlannedSet
import app.dvcoach.engine.Policy
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// Field names follow the server's JSON (snake_case). See server/app/schemas.py.

@Serializable
data class HealthDto(
    val status: String,
    @SerialName("engine_version") val engineVersion: String,
    @SerialName("auth_mode") val authMode: String,
)

@Serializable
data class ProfileDto(
    val goal: String,
    @SerialName("training_months") val trainingMonths: Int,
    val sex: String? = null,
    @SerialName("wake_time") val wakeTime: String,
    @SerialName("window_start") val windowStart: String,
    @SerialName("window_end") val windowEnd: String,
    @SerialName("quiet_start") val quietStart: String,
    @SerialName("quiet_end") val quietEnd: String,
    @SerialName("prompt_limit") val promptLimit: Int,
    @SerialName("screening_flags") val screeningFlags: List<String> = emptyList(),
    @SerialName("clearance_confirmed") val clearanceConfirmed: Boolean = false,
)

@Serializable
data class OnboardingDto(
    val timezone: String,
    @SerialName("birth_year") val birthYear: Int,
    @SerialName("confirmed_adult") val confirmedAdult: Boolean,
    @SerialName("accepted_terms") val acceptedTerms: Boolean,
    val profile: ProfileDto,
)

@Serializable
data class OnboardingResultDto(@SerialName("user_id") val userId: String, val profile: ProfileDto)

@Serializable
data class MaxTestDto(
    val exercise: String = "pushup",
    val reps: Int,
    @SerialName("tested_on") val testedOn: String,
)

@Serializable
data class BodyMeasurementDto(
    @SerialName("measured_on") val measuredOn: String,
    @SerialName("height_cm") val heightCm: Double? = null,
    @SerialName("weight_kg") val weightKg: Double? = null,
    @SerialName("arm_span_cm") val armSpanCm: Double? = null,
    @SerialName("waist_cm") val waistCm: Double? = null,
    @SerialName("wrist_cm") val wristCm: Double? = null,
    val source: String = "tape",
)

@Serializable
data class ProfileLineDto(
    val key: String,
    val label: String,
    val headline: String,
    val detail: String,
    val value: Double? = null,
)

@Serializable
data class BodyProfileDto(@SerialName("measured_on") val measuredOn: String, val lines: List<ProfileLineDto>)

@Serializable
data class CheckinDto(
    val date: String,
    @SerialName("local_time") val localTime: String,
    @SerialName("sleep_quality") val sleepQuality: Int,
    val soreness: Int,
    val energy: Int,
    @SerialName("sleep_minutes") val sleepMinutes: Int? = null,
    val exercise: String = "pushup",
)

@Serializable
data class PlanDto(
    val date: String,
    val exercise: String,
    val kind: String,
    val sets: List<PlannedSet>,
    val policy: Policy,
    val reason: String,
    val readiness: Double,
    @SerialName("max_reps") val maxReps: Int,
    val load: Double,
    @SerialName("engine_version") val engineVersion: String,
    val source: String,
)

@Serializable
data class FallbackPlanDto(
    val date: String,
    val exercise: String,
    val sets: List<PlannedSet>,
    val policy: Policy,
    val reason: String,
    @SerialName("max_reps") val maxReps: Int,
    val load: Double,
    @SerialName("engine_version") val engineVersion: String,
    val checkin: CheckinDto,
)

@Serializable
data class SetLogDto(
    val id: String,
    val date: String,
    val exercise: String,
    @SerialName("set_ref") val setRef: String,
    @SerialName("target_reps") val targetReps: Int,
    @SerialName("done_reps") val doneReps: Int,
    val rating: String,
    @SerialName("logged_at") val loggedAt: String,
    @SerialName("local_time") val localTime: String,
)

@Serializable
data class SetLogBatchDto(val logs: List<SetLogDto>)

@Serializable
data class SetLogBatchResultDto(val accepted: Int, val duplicates: Int)

@Serializable
data class DayDto(
    val date: String,
    @SerialName("sets_done") val setsDone: Int,
    @SerialName("reps_done") val repsDone: Int,
    @SerialName("hard_sets") val hardSets: Int,
)

@Serializable
data class WeightDto(@SerialName("measured_on") val measuredOn: String, @SerialName("weight_kg") val weightKg: Double)

@Serializable
data class ProgressDto(
    val exercise: String,
    @SerialName("max_tests") val maxTests: List<MaxTestDto>,
    val days: List<DayDto>,
    val weights: List<WeightDto>,
)
