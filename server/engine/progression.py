"""Weekly progression: one small step at a time.

At the first check-in of each week the server reviews the week before (Monday to
Sunday) and moves one step:

- A strong week (at least 90% of planned sets done, at most 1 in 10 rated Hard) adds
  one set or one rep per set. Sets come first and the two alternate, following the
  "change one variable at a time, volume first" rule from Freeletics' coaching model.
- A rough week (under 70% done, or more than 1 in 4 rated Hard) takes one step back,
  removing extra reps before sets.
- Anything else holds. So does a week with fewer than 3 training days, which is too
  little to judge.

Reps per set never go above 60% of the max, which keeps every set well short of
failure. When neither sets nor reps can grow, the answer is a new max test or the
next push-up level, not more volume.
"""

import datetime as dt
from dataclasses import dataclass

from .common import round_half_up

MIN_TRAINING_DAYS = 3
STEP_UP_COMPLETION = 0.9
STEP_UP_MAX_HARD = 0.1
STEP_DOWN_COMPLETION = 0.7
STEP_DOWN_HARD = 0.25
REP_CEILING = 0.6
MAX_EXTRA_SETS = 4


def week_start(day: dt.date) -> dt.date:
    """The Monday of the week containing `day`."""
    return day - dt.timedelta(days=day.weekday())


@dataclass(frozen=True)
class WeekStats:
    training_days: int  # days with a training plan
    sets_planned: int
    sets_done: int  # with reps done; skipped sets and pain stops excluded
    hard_sets: int


@dataclass(frozen=True)
class Progression:
    extra_sets: int = 0
    extra_reps: int = 0
    last_step: str | None = None  # "sets" or "reps": which grew last, so the next step alternates


@dataclass(frozen=True)
class Review:
    progression: Progression
    decision: str  # up_sets, up_reps, down_sets, down_reps, hold, not_enough_data, at_ceiling
    note: str


def rep_ceiling(max_reps: int, base_reps: int) -> int:
    return max(base_reps, round_half_up(REP_CEILING * max_reps))


def review_week(
    stats: WeekStats,
    current: Progression,
    *,
    base_sets: int,
    set_limit: int,
    base_reps: int,
    max_reps: int,
) -> Review:
    """`base_sets` and `base_reps` are the plan's numbers before any progression;
    `set_limit` is the most sets the user's window and prompt limit allow."""
    if stats.training_days < MIN_TRAINING_DAYS or stats.sets_planned == 0:
        return Review(current, "not_enough_data", "Not enough training days last week to change anything.")

    completion = stats.sets_done / stats.sets_planned
    hard_rate = stats.hard_sets / stats.sets_done if stats.sets_done else 0.0
    summary = f"{round_half_up(completion * 100)}% done, {_hard_words(stats.hard_sets)}"
    sets_now = base_sets + current.extra_sets
    reps_now = base_reps + current.extra_reps

    if completion >= STEP_UP_COMPLETION and hard_rate <= STEP_UP_MAX_HARD:
        can_add_set = sets_now + 1 <= set_limit and current.extra_sets < MAX_EXTRA_SETS
        can_add_rep = reps_now + 1 <= rep_ceiling(max_reps, base_reps)
        prefer_sets = current.last_step != "sets"
        if can_add_set and (prefer_sets or not can_add_rep):
            return Review(
                Progression(current.extra_sets + 1, current.extra_reps, "sets"),
                "up_sets",
                f"+1 set a day after a strong week ({summary}).",
            )
        if can_add_rep:
            return Review(
                Progression(current.extra_sets, current.extra_reps + 1, "reps"),
                "up_reps",
                f"+1 rep per set after a strong week ({summary}).",
            )
        return Review(
            current,
            "at_ceiling",
            f"A strong week ({summary}), and you're at the most this plan allows. "
            "A new max test or the next push-up level will move you on.",
        )

    if completion < STEP_DOWN_COMPLETION or hard_rate > STEP_DOWN_HARD:
        why = f"a tough week ({summary})"
        if current.extra_reps > 0:
            return Review(
                Progression(current.extra_sets, current.extra_reps - 1, current.last_step),
                "down_reps",
                f"1 rep fewer per set after {why}.",
            )
        if sets_now > 2:
            return Review(
                Progression(current.extra_sets - 1, current.extra_reps, current.last_step),
                "down_sets",
                f"1 set fewer a day after {why}.",
            )
        if reps_now > 1:
            return Review(
                Progression(current.extra_sets, current.extra_reps - 1, current.last_step),
                "down_reps",
                f"1 rep fewer per set after {why}.",
            )
        return Review(current, "hold", f"Holding steady after {why}; the plan is already at its lightest.")

    return Review(current, "hold", f"Holding steady ({summary}).")


def _hard_words(hard: int) -> str:
    if hard == 0:
        return "no hard sets"
    return "1 hard set" if hard == 1 else f"{hard} hard sets"
