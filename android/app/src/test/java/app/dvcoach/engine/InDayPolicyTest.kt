package app.dvcoach.engine

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** Runs shared/policy_vectors.json, the same cases as server/tests/test_policy.py. */
class InDayPolicyTest {

    @Serializable
    private data class Vectors(
        @SerialName("default_policy") val defaultPolicy: JsonObject,
        val cases: List<Case>,
    )

    @Serializable
    private data class Case(
        val name: String,
        @SerialName("policy_overrides") val policyOverrides: JsonObject = JsonObject(emptyMap()),
        val sets: List<PlannedSet>,
        val logs: List<Log>,
        val expected: Expected,
    )

    @Serializable
    private data class Log(val ref: String, val rating: String, val at: String)

    @Serializable
    private data class Expected(
        val status: String,
        @SerialName("hard_sets") val hardSets: Int,
        val sets: List<ExpectedSet>,
    )

    @Serializable
    private data class ExpectedSet(
        val ref: String,
        val at: String,
        @SerialName("target_reps") val targetReps: Int,
        val status: String,
        val rating: String?,
    )

    private val json = Json { ignoreUnknownKeys = true }

    private fun vectors(): Vectors {
        val text = javaClass.classLoader!!.getResource("policy_vectors.json")!!.readText()
        return json.decodeFromString(text)
    }

    @Test
    fun everySharedCasePasses() {
        val vectors = vectors()
        assertTrue(vectors.cases.isNotEmpty())
        for (case in vectors.cases) {
            val policy = json.decodeFromJsonElement(
                Policy.serializer(),
                JsonObject(vectors.defaultPolicy + case.policyOverrides),
            )
            val logs = case.logs.map { LoggedSet(it.ref, Rating.fromWire(it.rating), it.at) }

            val day = InDayPolicy.apply(case.sets, policy, logs)

            assertEquals(case.name, case.expected.status, day.status.name.lowercase())
            assertEquals(case.name, case.expected.hardSets, day.hardSets)
            val actual = day.sets.map {
                ExpectedSet(it.ref, it.at, it.targetReps, it.status.name.lowercase(), it.rating?.wire)
            }
            assertEquals(case.name, case.expected.sets, actual)
        }
    }
}
