"""Push-up levels, easiest to hardest. Sets are always sized from the max at the current level."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Level:
    number: int
    key: str
    title: str  # "Knee push-up"
    plural: str  # "knee push-ups", used in sentences and reminders
    how: str


LEVELS = (
    Level(1, "wall", "Wall push-up", "wall push-ups", "Hands on a wall at shoulder height, feet a step back."),
    Level(2, "incline", "Incline push-up", "incline push-ups", "Hands on a sturdy table or bench, body in a straight line."),
    Level(3, "knee", "Knee push-up", "knee push-ups", "Knees on the floor, body straight from knees to head."),
    Level(4, "full", "Push-up", "push-ups", "The standard push-up, on hands and toes."),
    Level(5, "decline", "Decline push-up", "decline push-ups", "Feet raised on a step or chair, hands on the floor."),
)
DEFAULT_LEVEL = 4
MOVE_UP_AT = 20  # a max this high means the next level will train more than more reps here
MOVE_DOWN_BELOW = 5  # below this, sets at ~40-50% would be only 1-2 reps


def level(number: int) -> Level:
    if not 1 <= number <= len(LEVELS):
        raise ValueError(f"level must be 1-{len(LEVELS)}, got {number}")
    return LEVELS[number - 1]


@dataclass(frozen=True)
class Suggestion:
    direction: str  # "up" or "down"
    level: int
    message: str


def suggest(level_number: int, max_reps: int) -> Suggestion | None:
    current = level(level_number)
    if max_reps >= MOVE_UP_AT and level_number < len(LEVELS):
        nxt = level(level_number + 1)
        return Suggestion(
            "up",
            nxt.number,
            f"{max_reps} {current.plural} is a strong max. For your next max test, try {nxt.plural}.",
        )
    if max_reps < MOVE_DOWN_BELOW and level_number > 1:
        easier = level(level_number - 1)
        return Suggestion(
            "down",
            easier.number,
            f"With a max of {max_reps}, each set would be only a rep or two. "
            f"Test {easier.plural} instead and move back up as you get stronger.",
        )
    return None
