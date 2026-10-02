package app.dvcoach.engine

import app.dvcoach.core.Hhmm
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class FallbackPlannerTest {

    private val policy = Policy(
        onHard = OnHard(scaleRemainingReps = 0.8, delayRemainingMin = 30),
        endDayAfterHardSets = 2,
        minGapMin = 45,
        windowEnd = "19:00",
        quietHours = listOf("21:30", "07:00"),
    )
    private val lastSets = listOf("09:20", "10:45", "12:10", "13:40", "15:30", "17:20")
        .mapIndexed { i, at -> PlannedSet("s${i + 1}", at, 9) }

    private fun build(checkin: String, windowEnd: String = "19:00") =
        FallbackPlanner.build(lastSets, policy, "09:00", windowEnd, checkin)

    @Test
    fun repeatsTheLastPlanWithOneSetFewer() {
        val result = build("07:40")!!
        assertEquals(5, result.sets.size)
        assertTrue(result.sets.all { it.targetReps == 9 })
        assertEquals(listOf("s1", "s2", "s3", "s4", "s5"), result.sets.map { it.ref })
        val minutes = result.sets.map { Hhmm.toMinutes(it.at) }
        assertTrue(minutes.first() >= Hhmm.toMinutes("09:00"))
        assertTrue(minutes.last() <= Hhmm.toMinutes("19:00"))
        assertTrue(minutes.zipWithNext().all { (a, b) -> b - a >= 45 })
    }

    @Test
    fun lateCheckInFitsFewerSets() {
        val result = build("17:30")!!
        assertEquals(1, result.sets.size)
        assertTrue(result.sets[0].at >= "17:45")
    }

    @Test
    fun windowAlreadyOverGivesNoSets() {
        assertTrue(build("19:00")!!.sets.isEmpty())
    }

    @Test
    fun usesTheCurrentWindowEnd() {
        assertEquals("18:00", build("07:40", windowEnd = "18:00")!!.policy.windowEnd)
    }

    @Test
    fun needsAPreviousPlan() {
        assertNull(FallbackPlanner.build(emptyList(), policy, "09:00", "19:00", "07:40"))
    }
}
