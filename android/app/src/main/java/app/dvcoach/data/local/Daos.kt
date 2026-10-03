package app.dvcoach.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Transaction
import androidx.room.Upsert
import kotlinx.coroutines.flow.Flow

@Dao
interface ProfileDao {
    @Query("SELECT * FROM local_profile WHERE id = 0")
    fun observe(): Flow<LocalProfile?>

    @Query("SELECT * FROM local_profile WHERE id = 0")
    suspend fun get(): LocalProfile?

    @Upsert
    suspend fun upsert(profile: LocalProfile)
}

@Dao
abstract class PlanDao {
    @Query("SELECT * FROM plans WHERE date = :date AND exercise = :exercise")
    abstract fun observePlan(date: String, exercise: String): Flow<PlanEntity?>

    @Query("SELECT * FROM plans WHERE date = :date AND exercise = :exercise")
    abstract suspend fun getPlan(date: String, exercise: String): PlanEntity?

    @Query("SELECT * FROM planned_sets WHERE date = :date AND exercise = :exercise ORDER BY orderIndex")
    abstract fun observeSets(date: String, exercise: String): Flow<List<PlannedSetEntity>>

    @Query("SELECT * FROM planned_sets WHERE date = :date AND exercise = :exercise ORDER BY orderIndex")
    abstract suspend fun getSets(date: String, exercise: String): List<PlannedSetEntity>

    /** The most recent plan that had training sets, used by the offline fallback planner. */
    @Query(
        """
        SELECT * FROM plans p
        WHERE p.exercise = :exercise AND p.date < :before
          AND EXISTS (SELECT 1 FROM planned_sets s WHERE s.date = p.date AND s.exercise = p.exercise)
        ORDER BY p.date DESC LIMIT 1
        """
    )
    abstract suspend fun latestWithSets(exercise: String, before: String): PlanEntity?

    @Query("SELECT * FROM plans WHERE source = 'fallback' AND uploaded = 0")
    abstract suspend fun fallbackPlansToUpload(): List<PlanEntity>

    @Query("UPDATE plans SET uploaded = 1 WHERE date = :date AND exercise = :exercise")
    abstract suspend fun markUploaded(date: String, exercise: String)

    @Query("UPDATE planned_sets SET snoozedUntil = :until WHERE date = :date AND exercise = :exercise AND ref = :ref")
    abstract suspend fun snooze(date: String, exercise: String, ref: String, until: String)

    @Upsert
    abstract suspend fun upsertPlan(plan: PlanEntity)

    @Upsert
    abstract suspend fun upsertSets(sets: List<PlannedSetEntity>)

    @Query("DELETE FROM planned_sets WHERE date = :date AND exercise = :exercise")
    abstract suspend fun deleteSets(date: String, exercise: String)

    @Query("DELETE FROM plans WHERE date = :date AND exercise = :exercise")
    abstract suspend fun deletePlan(date: String, exercise: String)

    @Transaction
    open suspend fun replace(plan: PlanEntity, sets: List<PlannedSetEntity>) {
        deleteSets(plan.date, plan.exercise)
        upsertPlan(plan)
        upsertSets(sets)
    }

    @Transaction
    open suspend fun deleteDay(date: String, exercise: String) {
        deleteSets(date, exercise)
        deletePlan(date, exercise)
    }
}

@Dao
interface LogDao {
    @Query("SELECT * FROM set_logs WHERE date = :date AND exercise = :exercise ORDER BY loggedAtEpochMs")
    fun observeForDay(date: String, exercise: String): Flow<List<SetLogEntity>>

    @Query("SELECT * FROM set_logs WHERE date = :date AND exercise = :exercise ORDER BY loggedAtEpochMs")
    suspend fun getForDay(date: String, exercise: String): List<SetLogEntity>

    @Insert(onConflict = OnConflictStrategy.IGNORE)
    suspend fun insert(log: SetLogEntity)

    @Query("SELECT * FROM set_logs WHERE synced = 0 ORDER BY loggedAtEpochMs LIMIT 500")
    suspend fun unsynced(): List<SetLogEntity>

    @Query("UPDATE set_logs SET synced = 1 WHERE id IN (:ids)")
    suspend fun markSynced(ids: List<String>)

    @Query("DELETE FROM set_logs WHERE date = :date AND exercise = :exercise")
    suspend fun deleteForDay(date: String, exercise: String)
}

@Dao
interface CheckinDao {
    @Query("SELECT * FROM checkins WHERE date = :date")
    fun observe(date: String): Flow<CheckinEntity?>

    @Query("SELECT * FROM checkins WHERE date = :date")
    suspend fun get(date: String): CheckinEntity?

    @Upsert
    suspend fun upsert(checkin: CheckinEntity)

    @Query("DELETE FROM checkins WHERE date = :date")
    suspend fun delete(date: String)
}
