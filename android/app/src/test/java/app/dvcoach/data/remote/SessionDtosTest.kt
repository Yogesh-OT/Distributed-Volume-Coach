package app.dvcoach.data.remote

import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.jsonObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Decodes real server responses from shared/session_samples.json, written by
 * server/tests/test_session_api.py, so a renamed field on either side fails here.
 */
class SessionDtosTest {
    private val samples: JsonObject by lazy {
        val text = javaClass.classLoader!!.getResource("session_samples.json")!!.readText()
        Api.json.parseToJsonElement(text).jsonObject
    }

    private inline fun <reified T> decode(key: String): T =
        Api.json.decodeFromJsonElement(kotlinx.serialization.serializer<T>(), samples.getValue(key))

    @Test
    fun sessionDecodes() {
        val session = decode<SessionDto>("session")
        assertEquals("A", session.template)
        val push = session.payload.pairs.first().first()
        assertEquals("push", push.ladder)
        assertTrue(push.sets > 0 && push.restSeconds == 60)
    }

    @Test
    fun summaryReportAndLibraryDecode() {
        assertTrue(decode<SessionSummaryDto>("summary").steps.isNotEmpty())
        val report = decode<ReportDto>("report")
        assertEquals(listOf(10, 20), report.targetBand)
        assertTrue(report.muscles.any { it.muscle == "chest" && it.sets > 0 })
        assertTrue(decode<LibraryDto>("library").ladders.any { it.key == "row" })
        assertTrue(decode<List<ExerciseStateDto>>("states").any { it.ladder == "push" })
        assertEquals(3, decode<SessionSettingsDto>("settings").daysPerWeek)
    }
}
