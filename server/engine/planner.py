"""Builds today's plan at check-in time.

Formulas (see the architecture page, "The engine"):

    p        load by experience: 0.40 / 0.45 / 0.50
    reps     r = round(p * M)
    base     N = min(cap, prompt limit, whole hours in the window)
    R        readiness, 0..1
    today    N_today = round(N * (0.6 + 0.4 * R)); R < 0.25 -> mobility-only day
    gaps     at least 45 minutes, spread over what is left of the window
"""

import math
import random
from dataclasses import dataclass

from . import ENGINE_VERSION
from .common import (
    EXERCISE_NAMES,
    LOAD,
    SET_CAP,
    Experience,
    experience_for,
    round_half_up,
    to_hhmm,
    to_minutes,
)
from .levels import DEFAULT_LEVEL, level as level_info
from .plan import Plan, PlanKind, PlannedSet, Policy
from .progression import rep_ceiling
from .readiness import describe, readiness

MOBILITY_ONLY_BELOW = 0.25
CHECKIN_LEAD_MIN = 15  # first set comes at least this long after check-in


@dataclass(frozen=True)
class PlannerInput:
    date: str
    exercise: str
    checkin_time: str  # local HH:MM
    window_start: str
    window_end: str
    quiet_hours: tuple[str, str]
    prompt_limit: int
    training_months: int
    max_reps: int
    sleep_quality: int
    soreness: int
    energy: int
    seed: str  # makes slot jitter repeatable, e.g. "<user id>:<date>"
    level: int = DEFAULT_LEVEL  # the level the max test was done at
    extra_sets: int = 0  # from the weekly review, see engine/progression.py
    extra_reps: int = 0
    progression_note: str | None = None  # why this week differs, added to the reason


def set_limits(experience: Experience, prompt_limit: int, window_minutes: int) -> tuple[int, int]:
    """(sets before progression, most sets the prompt limit and window allow)."""
    limit = min(prompt_limit, window_minutes // 60)
    return min(SET_CAP[experience], limit), limit


def base_reps_for(experience: Experience, max_reps: int) -> int:
    return max(1, round_half_up(LOAD[experience] * max_reps))


def build_plan(inp: PlannerInput) -> Plan:
    if inp.max_reps < 1:
        raise ValueError("max_reps must be at least 1")
    window_start, window_end = to_minutes(inp.window_start), to_minutes(inp.window_end)
    if window_end <= window_start:
        raise ValueError("the training window must end after it starts, on the same day")

    experience = experience_for(inp.training_months)
    load = LOAD[experience]
    ready = readiness(inp.sleep_quality, inp.soreness, inp.energy)
    summary = describe(inp.sleep_quality, inp.soreness, inp.energy)
    policy = Policy(window_end=inp.window_end, quiet_hours=inp.quiet_hours)
    name = EXERCISE_NAMES.get(inp.exercise, inp.exercise)
    level = level_info(inp.level)

    def plan(kind: PlanKind, sets: list[PlannedSet], reason: str) -> Plan:
        return Plan(
            date=inp.date,
            exercise=inp.exercise,
            kind=kind,
            sets=sets,
            policy=policy,
            reason=reason,
            readiness=round(ready, 2),
            max_reps=inp.max_reps,
            load=load,
            engine_version=ENGINE_VERSION,
            level=level.number,
        )

    if ready < MOBILITY_ONLY_BELOW:
        return plan(PlanKind.MOBILITY, [], f"{summary}: no {name} today. Gentle mobility only, and rest.")

    base, limit = set_limits(experience, inp.prompt_limit, window_end - window_start)
    sets_today = max(1, min(base + inp.extra_sets, limit))
    wanted = max(1, round_half_up(sets_today * (0.6 + 0.4 * ready)))
    base_reps = base_reps_for(experience, inp.max_reps)
    reps = max(1, min(base_reps + inp.extra_reps, rep_ceiling(inp.max_reps, base_reps)))

    start = max(window_start, to_minutes(inp.checkin_time) + CHECKIN_LEAD_MIN)
    available = window_end - start
    if available < 0:
        return plan(PlanKind.WINDOW_PASSED, [], "Your training window has ended for today. See you tomorrow.")

    fits = max(1, available // policy.min_gap_min)
    count = min(wanted, fits)
    times = spread(start, available, count, policy.min_gap_min, random.Random(inp.seed))
    sets = [PlannedSet(ref=f"s{i + 1}", at=to_hhmm(t), target_reps=reps) for i, t in enumerate(times)]

    sets_word = "set" if count == 1 else "sets"
    reason = (
        f"{summary}: {count} {sets_word} of {reps} {level.plural} "
        f"({round_half_up(reps / inp.max_reps * 100)}% of your {inp.max_reps}-rep max)."
    )
    if count < wanted:
        reason += f" {wanted - count} fewer than usual because of the late check-in."
    if inp.progression_note:
        reason += f" This week: {inp.progression_note}"
    return plan(PlanKind.TRAINING, sets, reason)


def spread(start: int, available: int, count: int, min_gap: int, rng: random.Random) -> list[int]:
    """Place `count` sets in [start, start + available] at least `min_gap` apart.

    Each set sits in the middle of an equal segment, then moves by a random amount
    small enough that neighbours stay `min_gap` apart. Callers guarantee that
    available // count >= min_gap whenever count > 1.
    """
    segment = available / count
    jitter = max(0, (math.floor(segment) - min_gap) // 2)
    return [
        start + math.floor(i * segment + segment / 2) + rng.randint(-jitter, jitter)
        for i in range(count)
    ]
