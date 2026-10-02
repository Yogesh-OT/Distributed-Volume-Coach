def readiness(sleep_quality: int, soreness: int, energy: int) -> float:
    """Morning readiness from 0 (worst) to 1 (best).

    Each answer is on a 1-5 scale. Soreness is inverted because more soreness means
    less ready.
    """
    for name, value in (("sleep_quality", sleep_quality), ("soreness", soreness), ("energy", energy)):
        if not 1 <= value <= 5:
            raise ValueError(f"{name} must be 1-5, got {value}")
    return ((sleep_quality - 1) / 4 + (5 - soreness) / 4 + (energy - 1) / 4) / 3


def describe(sleep_quality: int, soreness: int, energy: int) -> str:
    """Plain-language summary of a check-in, used at the start of a plan's reason."""
    notes = []
    if sleep_quality >= 4:
        notes.append("good sleep")
    elif sleep_quality <= 2:
        notes.append("poor sleep")
    if energy >= 4:
        notes.append("good energy")
    elif energy <= 2:
        notes.append("low energy")
    if soreness <= 2:
        notes.append("low soreness")
    elif soreness >= 4:
        notes.append("high soreness")
    if not notes:
        return "An average morning"
    text = notes[0] if len(notes) == 1 else ", ".join(notes[:-1]) + " and " + notes[-1]
    return text[0].upper() + text[1:]
