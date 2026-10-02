from dataclasses import dataclass
from datetime import date, timedelta

# Screening flags, based on the PAR-Q+ general health questions plus current pain.
# The question wording lives in the app; check the PAR-Q+ Collaboration's terms of
# use before shipping the official wording.
SCREENING_FLAGS = (
    "heart_condition",
    "chest_pain",
    "dizziness",
    "chronic_condition",
    "medication",
    "bone_joint_problem",
    "supervised_only",
    "current_pain",
)

MAX_TEST_INTERVAL_DAYS = 14
MIN_AGE = 18


@dataclass(frozen=True)
class Eligibility:
    allowed: bool
    code: str | None = None
    message: str | None = None
    next_allowed: date | None = None


def is_adult(birth_year: int, today: date, confirmed_adult: bool) -> bool:
    """Birth year alone can't separate 17 from 18, so the user also confirms."""
    return confirmed_adult and today.year - birth_year >= MIN_AGE


def max_test_eligibility(
    flags: list[str], clearance_confirmed: bool, last_test: date | None, today: date
) -> Eligibility:
    if flags and not clearance_confirmed:
        return Eligibility(
            False,
            "clearance_required",
            "Your screening answers suggest checking with a doctor first. "
            "Confirm in your profile once a doctor has cleared you for exercise.",
        )
    if last_test is not None:
        next_allowed = last_test + timedelta(days=MAX_TEST_INTERVAL_DAYS)
        if today < next_allowed:
            return Eligibility(
                False,
                "too_soon",
                f"Max tests are spaced at least {MAX_TEST_INTERVAL_DAYS} days apart.",
                next_allowed,
            )
    return Eligibility(True)
