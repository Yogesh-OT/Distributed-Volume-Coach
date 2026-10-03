package app.dvcoach.engine

/** Mirrors server/engine/levels.py: easiest first, and the same thresholds. */
data class PushupLevel(val number: Int, val title: String, val plural: String, val how: String)

object Levels {
    val ALL = listOf(
        PushupLevel(1, "Wall push-up", "wall push-ups", "Hands on a wall at shoulder height, feet a step back."),
        PushupLevel(2, "Incline push-up", "incline push-ups", "Hands on a sturdy table or bench, body in a straight line."),
        PushupLevel(3, "Knee push-up", "knee push-ups", "Knees on the floor, body straight from knees to head."),
        PushupLevel(4, "Push-up", "push-ups", "The standard push-up, on hands and toes."),
        PushupLevel(5, "Decline push-up", "decline push-ups", "Feet raised on a step or chair, hands on the floor."),
    )
    const val DEFAULT = 4
    const val MOVE_UP_AT = 20
    const val MOVE_DOWN_BELOW = 5

    fun of(number: Int?): PushupLevel = ALL.getOrNull((number ?: DEFAULT) - 1) ?: ALL[DEFAULT - 1]

    /** Same advice as the server's suggest(): a level up at 20+, a level down below 5. */
    fun suggestion(level: Int, maxReps: Int): String? {
        val current = of(level)
        return when {
            maxReps >= MOVE_UP_AT && level < ALL.size ->
                "$maxReps ${current.plural} is a strong max. For your next max test, try ${of(level + 1).plural}."
            maxReps < MOVE_DOWN_BELOW && level > 1 ->
                "With a max of $maxReps, each set would be only a rep or two. " +
                    "Test ${of(level - 1).plural} instead and move back up as you get stronger."
            else -> null
        }
    }
}
