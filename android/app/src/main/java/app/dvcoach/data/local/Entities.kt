package app.dvcoach.data.local

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

/** The questionnaire answers this phone last sent, plus the latest max test. One row. */
@Entity(tableName = "local_profile")
data class LocalProfile(
    @PrimaryKey val id: Int = 0,
    val timezone: String,
    val goal: String,
    val trainingMonths: Int,
    val sex: String?,
    val wakeTime: String,
    val windowStart: String,
    val windowEnd: String,
    val quietStart: String,
    val quietEnd: String,
    val promptLimit: Int,
    val screeningFlags: String, // comma-separated
    val clearanceConfirmed: Boolean,
    val maxReps: Int? = null,
    val lastMaxTestDate: String? = null,
) {
    // A function, not a property, so Room doesn't try to store it as a column.
    fun flagList(): List<String> = screeningFlags.split(",").filter { it.isNotBlank() }
}

@Entity(tableName = "plans", primaryKeys = ["date", "exercise"])
data class PlanEntity(
    val date: String,
    val exercise: String,
    val kind: String, // training, mobility, window_passed
    val policyJson: String,
    val reason: String,
    val readiness: Double?,
    val maxReps: Int,
    val load: Double,
    val engineVersion: String,
    val source: String, // server or fallback
    val uploaded: Boolean, // fallback plans upload once a connection returns
    val checkinJson: String?, // sent along with a fallback plan
)

@Entity(tableName = "planned_sets", primaryKeys = ["date", "exercise", "ref"])
data class PlannedSetEntity(
    val date: String,
    val exercise: String,
    val ref: String,
    val orderIndex: Int,
    val at: String,
    val targetReps: Int,
    val snoozedUntil: String? = null,
)

@Entity(tableName = "set_logs", indices = [Index("synced"), Index(value = ["date", "exercise"])])
data class SetLogEntity(
    @PrimaryKey val id: String, // made here, so retried uploads never count twice
    val date: String,
    val exercise: String,
    val setRef: String,
    val targetReps: Int,
    val doneReps: Int,
    val rating: String,
    val loggedAtEpochMs: Long,
    val localTime: String,
    val loggedAtIso: String, // with offset, e.g. 2026-10-05T09:26:41+05:30
    val synced: Boolean = false,
)

@Entity(tableName = "checkins")
data class CheckinEntity(
    @PrimaryKey val date: String,
    val localTime: String,
    val sleepQuality: Int,
    val soreness: Int,
    val energy: Int,
)
