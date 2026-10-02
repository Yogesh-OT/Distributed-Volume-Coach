import math
from enum import StrEnum


class Experience(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    EXPERIENCED = "experienced"


# Fraction of the user's max reps done in each set (common Grease the Groove practice).
LOAD = {
    Experience.BEGINNER: 0.40,
    Experience.INTERMEDIATE: 0.45,
    Experience.EXPERIENCED: 0.50,
}

# Most sets in a day before readiness scaling.
SET_CAP = {
    Experience.BEGINNER: 5,
    Experience.INTERMEDIATE: 7,
    Experience.EXPERIENCED: 8,
}

EXERCISE_NAMES = {"pushup": "push-ups"}


def experience_for(training_months: int) -> Experience:
    if training_months < 0:
        raise ValueError("training_months must be zero or more")
    if training_months < 6:
        return Experience.BEGINNER
    if training_months < 24:
        return Experience.INTERMEDIATE
    return Experience.EXPERIENCED


def round_half_up(x: float) -> int:
    """Round halves up, like Kotlin's roundToInt().

    Python's round() rounds halves to even (round(4.5) == 4), which would make the
    server and the phone disagree. The tiny epsilon absorbs float error such as
    0.9 * 5 == 4.499999999.
    """
    return math.floor(x + 0.5 + 1e-9)


def to_minutes(hhmm: str) -> int:
    """'07:40' -> 460 minutes after local midnight."""
    try:
        hours, minutes = hhmm.split(":")
        h, m = int(hours), int(minutes)
    except ValueError as exc:
        raise ValueError(f"expected HH:MM, got {hhmm!r}") from exc
    if not (0 <= h < 24 and 0 <= m < 60):
        raise ValueError(f"time out of range: {hhmm!r}")
    return h * 60 + m


def to_hhmm(minutes: int) -> str:
    if not 0 <= minutes < 24 * 60:
        raise ValueError(f"minutes out of range: {minutes}")
    return f"{minutes // 60:02d}:{minutes % 60:02d}"
