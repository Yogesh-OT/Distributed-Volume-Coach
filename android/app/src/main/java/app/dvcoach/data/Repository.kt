package app.dvcoach.data

import android.content.Context
import android.util.Log
import app.dvcoach.core.Hhmm
import app.dvcoach.data.local.AppDatabase
import app.dvcoach.data.local.CheckinEntity
import app.dvcoach.data.local.LocalProfile
import app.dvcoach.data.local.PlanEntity
import app.dvcoach.data.local.PlannedSetEntity
import app.dvcoach.data.local.SetLogEntity
import app.dvcoach.data.remote.Api
import app.dvcoach.data.remote.ApiResult
import app.dvcoach.data.remote.BodyMeasurementDto
import app.dvcoach.data.remote.BodyProfileDto
import app.dvcoach.data.remote.CheckinDto
import app.dvcoach.data.remote.CoachApi
import app.dvcoach.data.remote.FallbackPlanDto
import app.dvcoach.data.remote.MaxTestDto
import app.dvcoach.data.remote.OnboardingDto
import app.dvcoach.data.remote.ProfileDto
import app.dvcoach.data.remote.ProgressDto
import app.dvcoach.data.remote.SetLogBatchDto
import app.dvcoach.data.remote.SetLogDto
import app.dvcoach.data.remote.apiCall
import app.dvcoach.engine.DayState
import app.dvcoach.engine.DayStatus
import app.dvcoach.engine.FallbackPlanner
import app.dvcoach.engine.InDayPolicy
import app.dvcoach.engine.LoggedSet
import app.dvcoach.engine.PlannedSet
import app.dvcoach.engine.Policy
import app.dvcoach.engine.Rating
import app.dvcoach.engine.SetStatus
import app.dvcoach.reminders.Notifier
import app.dvcoach.reminders.PromptScheduler
import app.dvcoach.sync.SyncWorker
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.withContext
import retrofit2.HttpException
import java.io.IOException
import java.time.Clock
import java.time.LocalDate
import java.time.LocalTime
import java.time.ZonedDateTime
import java.util.UUID
import kotlin.math.min

/**
 * Everything the screens, alarms and sync worker do goes through here.
 * Today's plan, the in-day rules and the logs live on the phone, so a day keeps working offline.
 */
class Repository(
    private val context: Context,
    private val db: AppDatabase,
    private val api: CoachApi,
    private val scheduler: PromptScheduler,
    private val clock: Clock = Clock.systemDefaultZone(),
) {
    companion object {
        const val EXERCISE = "pushup"
        const val SNOOZE_MIN = 15
        private const val TAG = "Repository"
    }

    data class Today(val date: String, val plan: PlanEntity?, val day: DayState?, val checkedIn: Boolean)

    sealed interface CheckInOutcome {
        data class Planned(val reason: String, val offline: Boolean) : CheckInOutcome
        data class Failed(val message: String) : CheckInOutcome
    }

    private val profileDao = db.profileDao()
    private val planDao = db.planDao()
    private val logDao = db.logDao()
    private val checkinDao = db.checkinDao()

    val profile: Flow<LocalProfile?> = profileDao.observe()

    fun today(): LocalDate = LocalDate.now(clock)

    private fun nowHhmm(): String = Hhmm.of(LocalTime.now(clock))

    // ---- Today ----

    fun observeToday(): Flow<Today> {
        val date = today().toString()
        return combine(
            planDao.observePlan(date, EXERCISE),
            planDao.observeSets(date, EXERCISE),
            logDao.observeForDay(date, EXERCISE),
            checkinDao.observe(date),
        ) { plan, sets, logs, checkin ->
            Today(date, plan, plan?.let { dayState(it, sets, logs) }, checkedIn = checkin != null)
        }
    }

    private fun decodePolicy(json: String): Policy = Api.json.decodeFromString(Policy.serializer(), json)

    private fun dayState(plan: PlanEntity, sets: List<PlannedSetEntity>, logs: List<SetLogEntity>): DayState =
        InDayPolicy.apply(
            sets.map { PlannedSet(it.ref, it.snoozedUntil ?: it.at, it.targetReps) },
            decodePolicy(plan.policyJson),
            logs.map { LoggedSet(it.setRef, Rating.fromWire(it.rating), it.localTime) },
        )

    private suspend fun loadDay(date: String): Pair<PlanEntity, DayState>? {
        val plan = planDao.getPlan(date, EXERCISE) ?: return null
        return plan to dayState(plan, planDao.getSets(date, EXERCISE), logDao.getForDay(date, EXERCISE))
    }

    // ---- Onboarding, profile, max test, body ----

    suspend fun onboard(form: OnboardingDto): ApiResult<Unit> {
        val profile = when (val result = apiCall { api.onboard(form) }) {
            is ApiResult.Ok -> result.value.profile
            // Same sign-in onboarded before (for example after clearing app data): reuse that profile.
            is ApiResult.Failed -> if (result.code == "already_onboarded") {
                when (val existing = apiCall { api.profile() }) {
                    is ApiResult.Ok -> existing.value
                    is ApiResult.Failed -> return existing
                }
            } else {
                return result
            }
        }
        saveProfile(form.timezone, profile)
        scheduleCheckinReminder()
        return ApiResult.Ok(Unit)
    }

    private suspend fun saveProfile(timezone: String, dto: ProfileDto) {
        val existing = profileDao.get()
        profileDao.upsert(
            LocalProfile(
                timezone = timezone,
                goal = dto.goal,
                trainingMonths = dto.trainingMonths,
                sex = dto.sex,
                wakeTime = dto.wakeTime,
                windowStart = dto.windowStart,
                windowEnd = dto.windowEnd,
                quietStart = dto.quietStart,
                quietEnd = dto.quietEnd,
                promptLimit = dto.promptLimit,
                screeningFlags = dto.screeningFlags.joinToString(","),
                clearanceConfirmed = dto.clearanceConfirmed,
                maxReps = existing?.maxReps,
                lastMaxTestDate = existing?.lastMaxTestDate,
            )
        )
    }

    private fun LocalProfile.toDto() = ProfileDto(
        goal = goal,
        trainingMonths = trainingMonths,
        sex = sex,
        wakeTime = wakeTime,
        windowStart = windowStart,
        windowEnd = windowEnd,
        quietStart = quietStart,
        quietEnd = quietEnd,
        promptLimit = promptLimit,
        screeningFlags = flagList(),
        clearanceConfirmed = clearanceConfirmed,
    )

    suspend fun confirmClearance(): ApiResult<Unit> {
        val local = profileDao.get() ?: return ApiResult.Failed("Finish onboarding first.")
        return when (val result = apiCall { api.updateProfile(local.toDto().copy(clearanceConfirmed = true)) }) {
            is ApiResult.Ok -> {
                profileDao.upsert(local.copy(clearanceConfirmed = true))
                ApiResult.Ok(Unit)
            }
            is ApiResult.Failed -> result
        }
    }

    suspend fun recordMaxTest(reps: Int): ApiResult<Unit> {
        val date = today().toString()
        return when (val result = apiCall { api.recordMaxTest(MaxTestDto(reps = reps, testedOn = date)) }) {
            is ApiResult.Ok -> {
                profileDao.get()?.let { profileDao.upsert(it.copy(maxReps = reps, lastMaxTestDate = date)) }
                ApiResult.Ok(Unit)
            }
            is ApiResult.Failed -> result
        }
    }

    suspend fun addMeasurements(measurements: BodyMeasurementDto): ApiResult<BodyProfileDto> =
        apiCall { api.addMeasurements(measurements.copy(measuredOn = today().toString())) }

    suspend fun bodyProfile(): ApiResult<BodyProfileDto> = apiCall { api.bodyProfile() }

    suspend fun progress(): ApiResult<ProgressDto> = apiCall { api.progress() }

    // ---- Check-in and plans ----

    suspend fun checkIn(sleepQuality: Int, soreness: Int, energy: Int): CheckInOutcome {
        val profile = profileDao.get() ?: return CheckInOutcome.Failed("Finish onboarding first.")
        val checkin = CheckinDto(today().toString(), nowHhmm(), sleepQuality, soreness, energy)
        checkinDao.upsert(CheckinEntity(checkin.date, checkin.localTime, sleepQuality, soreness, energy))
        scheduleCheckinReminder() // moves to tomorrow

        return when (val result = apiCall { api.checkIn(checkin) }) {
            is ApiResult.Ok -> {
                val plan = result.value
                storePlan(
                    PlanEntity(
                        date = plan.date,
                        exercise = plan.exercise,
                        kind = plan.kind,
                        policyJson = Api.json.encodeToString(Policy.serializer(), plan.policy),
                        reason = plan.reason,
                        readiness = plan.readiness,
                        maxReps = plan.maxReps,
                        load = plan.load,
                        engineVersion = plan.engineVersion,
                        source = plan.source,
                        uploaded = true,
                        checkinJson = null,
                    ),
                    plan.sets,
                )
                CheckInOutcome.Planned(plan.reason, offline = false)
            }
            is ApiResult.Failed ->
                if (result.offline) planOffline(profile, checkin) else CheckInOutcome.Failed(result.message)
        }
    }

    private suspend fun planOffline(profile: LocalProfile, checkin: CheckinDto): CheckInOutcome {
        val last = planDao.latestWithSets(EXERCISE, before = checkin.date)
            ?: return CheckInOutcome.Failed(
                "Can't reach the server, and there's no earlier plan to repeat. Connect once to get your first plan."
            )
        val lastSets = planDao.getSets(last.date, EXERCISE).map { PlannedSet(it.ref, it.at, it.targetReps) }
        val result = FallbackPlanner.build(
            lastSets, decodePolicy(last.policyJson), profile.windowStart, profile.windowEnd, checkin.localTime,
        ) ?: return CheckInOutcome.Failed("Can't reach the server. Try again in a moment.")

        storePlan(
            PlanEntity(
                date = checkin.date,
                exercise = EXERCISE,
                kind = if (result.sets.isEmpty()) "window_passed" else "training",
                policyJson = Api.json.encodeToString(Policy.serializer(), result.policy),
                reason = result.reason,
                readiness = null,
                maxReps = last.maxReps,
                load = last.load,
                engineVersion = FallbackPlanner.ENGINE_VERSION,
                source = "fallback",
                uploaded = result.sets.isEmpty(), // nothing worth uploading
                checkinJson = Api.json.encodeToString(CheckinDto.serializer(), checkin),
            ),
            result.sets,
        )
        SyncWorker.enqueue(context)
        return CheckInOutcome.Planned(result.reason, offline = true)
    }

    private suspend fun storePlan(plan: PlanEntity, sets: List<PlannedSet>) {
        planDao.replace(
            plan,
            sets.mapIndexed { i, s -> PlannedSetEntity(plan.date, plan.exercise, s.ref, i, s.at, s.targetReps) },
        )
        rescheduleDay(plan.date)
    }

    // ---- Logging ----

    suspend fun logSet(date: String, ref: String, rating: Rating, doneReps: Int? = null) {
        val (_, day) = loadDay(date) ?: return
        if (day.status != DayStatus.ACTIVE) return
        val set = day.sets.firstOrNull { it.ref == ref && it.status == SetStatus.PENDING } ?: return

        val now = ZonedDateTime.now(clock)
        val done = when (rating) {
            Rating.SKIPPED -> 0
            Rating.PAIN -> doneReps ?: 0
            else -> doneReps ?: set.targetReps
        }
        logDao.insert(
            SetLogEntity(
                id = UUID.randomUUID().toString(),
                date = date,
                exercise = EXERCISE,
                setRef = ref,
                targetReps = set.targetReps,
                doneReps = done,
                rating = rating.wire,
                loggedAtEpochMs = now.toInstant().toEpochMilli(),
                localTime = Hhmm.of(now.toLocalTime()),
                loggedAtIso = now.toOffsetDateTime().toString(),
            )
        )
        Notifier.cancelSetPrompt(context, ref)
        rescheduleDay(date)
        SyncWorker.enqueue(context)
    }

    suspend fun snooze(date: String, ref: String) {
        val (plan, _) = loadDay(date) ?: return
        val windowEnd = Hhmm.toMinutes(decodePolicy(plan.policyJson).windowEnd)
        val until = min(Hhmm.toMinutes(nowHhmm()) + SNOOZE_MIN, windowEnd)
        planDao.snooze(date, EXERCISE, ref, Hhmm.format(until))
        Notifier.cancelSetPrompt(context, ref)
        rescheduleDay(date)
    }

    // ---- Alarms ----

    suspend fun onPromptDue(date: String, ref: String) {
        if (date != today().toString()) return
        val (_, day) = loadDay(date) ?: return
        val set = day.sets.firstOrNull { it.ref == ref } ?: return
        if (day.status != DayStatus.ACTIVE || set.status != SetStatus.PENDING) return
        // The set moved later (a hard set or a snooze) and has its own new alarm.
        if (Hhmm.toMinutes(set.at) > Hhmm.toMinutes(nowHhmm()) + 5) return
        Notifier.showSetPrompt(context, date, set, day.sets.map { it.ref })
    }

    suspend fun onCheckinReminderDue() {
        val date = today().toString()
        val profile = profileDao.get()
        if (profile?.maxReps != null && checkinDao.get(date) == null && planDao.getPlan(date, EXERCISE) == null) {
            Notifier.showCheckinReminder(context)
        }
        scheduleCheckinReminder()
    }

    suspend fun rescheduleAll() {
        rescheduleDay(today().toString())
        scheduleCheckinReminder()
    }

    private suspend fun rescheduleDay(date: String) {
        if (date != today().toString()) return
        val (_, day) = loadDay(date) ?: return
        val pending = if (day.status == DayStatus.ACTIVE) day.sets.filter { it.status == SetStatus.PENDING } else emptyList()
        scheduler.scheduleSets(LocalDate.parse(date), pending)
    }

    private suspend fun scheduleCheckinReminder() {
        val profile = profileDao.get() ?: return
        val checkedIn = checkinDao.get(today().toString()) != null
        scheduler.scheduleCheckinReminder(profile.wakeTime, checkedInToday = checkedIn)
    }

    // ---- Sync ----

    /** Returns false when it should be retried later (no connection or a server error). */
    suspend fun syncNow(): Boolean = try {
        for (plan in planDao.fallbackPlansToUpload()) {
            val sets = planDao.getSets(plan.date, plan.exercise).map { PlannedSet(it.ref, it.at, it.targetReps) }
            val checkin = plan.checkinJson?.let { Api.json.decodeFromString(CheckinDto.serializer(), it) }
            if (sets.isNotEmpty() && checkin != null) {
                api.uploadFallbackPlan(
                    FallbackPlanDto(
                        plan.date, plan.exercise, sets, decodePolicy(plan.policyJson), plan.reason,
                        plan.maxReps, plan.load, plan.engineVersion, checkin,
                    )
                )
            }
            planDao.markUploaded(plan.date, plan.exercise)
        }
        while (true) {
            val batch = logDao.unsynced()
            if (batch.isEmpty()) break
            api.uploadLogs(SetLogBatchDto(batch.map { it.toDto() }))
            logDao.markSynced(batch.map { it.id })
        }
        true
    } catch (e: IOException) {
        false
    } catch (e: HttpException) {
        // A 4xx means the server rejected the data itself; retrying won't change that.
        Log.w(TAG, "Sync rejected with HTTP ${e.code()}")
        e.code() < 500
    }

    private fun SetLogEntity.toDto() = SetLogDto(
        id = id,
        date = date,
        exercise = exercise,
        setRef = setRef,
        targetReps = targetReps,
        doneReps = doneReps,
        rating = rating,
        loggedAt = loggedAtIso,
        localTime = localTime,
    )

    // ---- Account ----

    suspend fun deleteAccount(): ApiResult<Unit> {
        val result = apiCall {
            val response = api.deleteAccount()
            if (!response.isSuccessful) throw HttpException(response)
        }
        if (result is ApiResult.Ok) {
            scheduler.cancelAll()
            withContext(Dispatchers.IO) { db.clearAllTables() }
        }
        return result
    }
}
