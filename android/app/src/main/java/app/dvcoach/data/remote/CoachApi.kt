package app.dvcoach.data.remote

import app.dvcoach.data.ServerConfig
import app.dvcoach.data.auth.AuthTokenProvider
import kotlinx.coroutines.runBlocking
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import retrofit2.HttpException
import retrofit2.Response
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Path
import retrofit2.http.Query
import java.io.IOException
import java.util.concurrent.TimeUnit

interface CoachApi {
    @GET("health")
    suspend fun health(): HealthDto

    @POST("v1/onboarding")
    suspend fun onboard(@Body body: OnboardingDto): OnboardingResultDto

    @GET("v1/profile")
    suspend fun profile(): ProfileDto

    @PUT("v1/profile")
    suspend fun updateProfile(@Body body: ProfileDto): ProfileDto

    @POST("v1/max-tests")
    suspend fun recordMaxTest(@Body body: MaxTestDto): MaxTestResultDto

    @GET("v1/streak")
    suspend fun streak(@Query("exercise") exercise: String = "pushup"): StreakDto

    @POST("v1/body-measurements")
    suspend fun addMeasurements(@Body body: BodyMeasurementDto): BodyProfileDto

    @GET("v1/body-profile")
    suspend fun bodyProfile(): BodyProfileDto

    @POST("v1/checkins")
    suspend fun checkIn(@Body body: CheckinDto): PlanDto

    @POST("v1/plans/fallback")
    suspend fun uploadFallbackPlan(@Body body: FallbackPlanDto): PlanDto

    @POST("v1/set-logs/batch")
    suspend fun uploadLogs(@Body body: SetLogBatchDto): SetLogBatchResultDto

    @GET("v1/progress")
    suspend fun progress(@Query("exercise") exercise: String = "pushup", @Query("days") days: Int = 56): ProgressDto

    @DELETE("v1/me")
    suspend fun deleteAccount(): Response<Unit>

    /** Only exists on a server running in dev mode. */
    @DELETE("v1/dev/days/{day}")
    suspend fun resetDay(@Path("day") day: String): Response<Unit>
}

object Api {
    val json = Json {
        ignoreUnknownKeys = true
        explicitNulls = false
        encodeDefaults = true
    }

    fun create(server: ServerConfig, tokens: AuthTokenProvider): CoachApi {
        val client = OkHttpClient.Builder()
            // A check-in that takes longer than this falls back to the offline planner.
            .callTimeout(10, TimeUnit.SECONDS)
            .addInterceptor { chain ->
                // Read the address on every call, so changing it in the app takes effect at once.
                val request = chain.request()
                val target = server.baseUrl().toHttpUrlOrNull()
                val url = if (target == null) {
                    request.url
                } else {
                    request.url.newBuilder().scheme(target.scheme).host(target.host).port(target.port).build()
                }
                val token = runBlocking { tokens.token() }
                chain.proceed(request.newBuilder().url(url).header("Authorization", "Bearer $token").build())
            }
            .build()
        return Retrofit.Builder()
            .baseUrl(server.baseUrl())
            .client(client)
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()
            .create(CoachApi::class.java)
    }
}

sealed interface ApiResult<out T> {
    data class Ok<T>(val value: T) : ApiResult<T>

    /** [code] is the server's stable error code, when it sent one. */
    data class Failed(
        val message: String,
        val code: String? = null,
        val offline: Boolean = false,
        val nextAllowed: String? = null,
    ) : ApiResult<Nothing>
}

suspend fun <T> apiCall(block: suspend () -> T): ApiResult<T> = try {
    ApiResult.Ok(block())
} catch (e: HttpException) {
    parseError(e)
} catch (e: IOException) {
    ApiResult.Failed("Can't reach the server. Check your connection and try again.", offline = true)
}

private fun parseError(e: HttpException): ApiResult.Failed {
    val fallback = ApiResult.Failed("Something went wrong on the server (${e.code()}). Try again later.")
    val body = e.response()?.errorBody()?.string() ?: return fallback
    val detail = runCatching { Api.json.parseToJsonElement(body).jsonObject["detail"] }.getOrNull() ?: return fallback
    return when (detail) {
        // Our own errors: {"code": "...", "message": "..."}
        is JsonObject -> ApiResult.Failed(
            message = detail["message"]?.jsonPrimitive?.contentOrNull ?: fallback.message,
            code = detail["code"]?.jsonPrimitive?.contentOrNull,
            nextAllowed = detail["next_allowed"]?.jsonPrimitive?.contentOrNull,
        )
        // FastAPI validation errors: [{"loc": ["body", "arm_span_cm"], "msg": "..."}]
        is JsonArray -> {
            val first = detail.firstOrNull() as? JsonObject
            val message = first?.get("msg")?.jsonPrimitive?.contentOrNull?.let(::friendlyMessage) ?: fallback.message
            val field = (first?.get("loc") as? JsonArray)?.lastOrNull()?.jsonPrimitive?.contentOrNull?.let(::fieldLabel)
            ApiResult.Failed(message = if (field != null) "$field: $message" else message, code = "invalid")
        }
        else -> fallback
    }
}

private val FIELD_LABELS = mapOf(
    "height_cm" to "Height",
    "weight_kg" to "Weight",
    "arm_span_cm" to "Arm span",
    "waist_cm" to "Waist",
    "wrist_cm" to "Wrist",
    "training_months" to "Months of training",
    "birth_year" to "Birth year",
    "prompt_limit" to "Prompts a day",
    "reps" to "Reps",
)

/** A readable name for the field an error is about, or null for errors about the whole form. */
private fun fieldLabel(name: String): String? = when {
    name == "body" || name.all { it.isDigit() } -> null
    else -> FIELD_LABELS[name] ?: name.replace('_', ' ').replaceFirstChar { it.uppercase() }
}

private fun friendlyMessage(msg: String): String = msg
    .removePrefix("Value error, ")
    .replace(Regex("^Input should be greater than or equal to (\\S+)$"), "must be at least $1")
    .replace(Regex("^Input should be less than or equal to (\\S+)$"), "must be at most $1")
