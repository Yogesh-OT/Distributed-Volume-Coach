"""Progression in session mode.

After each session, every exercise takes one small step (double progression, as in
the r/bodyweightfitness routine; see docs/training-research.md):

- All sets done with 2 or more reps left: +1 rep per set next time. If the last set
  showed far more in hand, the target catches up to 3 below what that set reached.
- A set rated Hard (1 left) or one missed set: same target, because that's the effort
  we're aiming for.
- Two or more sets missed or taken to the limit: 1 rep fewer.
- At the top of the range with reps to spare: the next level, starting at the bottom
  of its range.
- Below the range two sessions in a row: the level before.

Once a week, the volume step (sets per exercise, engine/sessions.py) moves by at most
one, from how much of the week was done, how many sets hit the limit, and soreness at
check-in.
"""

from dataclasses import dataclass, replace
from enum import StrEnum

from .exercises import (
    CIRCUIT_LEVELS,
    EVERYDAY,
    ExerciseState,
    Need,
    describe_target,
    ladder,
    next_usable,
    previous_usable,
)
from .sessions import MAX_STEP, MIN_STEP

MAX_WEEKLY_SETS = 20  # per muscle; more adds little (Pelland et al. 2026)
CATCH_UP_MARGIN = 3  # targets catch up to this many below what a test set reached
LEVEL_UP_SPARE = 2  # a test set this far past the top of the range moves you up
BELOW_RANGE_SESSIONS = 2


class Effort(StrEnum):
    EASY = "easy"  # 4 or more reps left
    GOOD = "good"  # 2-3 left
    HARD = "hard"  # 1 left
    MAX = "max"  # nothing left


@dataclass(frozen=True)
class SetResult:
    reps: int  # or seconds, for holds
    effort: Effort = Effort.GOOD
    pain: bool = False


@dataclass(frozen=True)
class Step:
    state: ExerciseState
    decision: str  # up_reps, catch_up, hold, down_reps, level_up, level_down, pain, skipped
    note: str


def after_session(
    state: ExerciseState,
    results: list[SetResult],
    *,
    tested: bool,
    available: frozenset[Need] = EVERYDAY,
) -> Step:
    """`tested` says whether the last set went as far as good form allowed."""
    lad = ladder(state.ladder)
    name = lad.at(state.level).name
    if not results:
        return Step(state, "skipped", f"{name}: skipped, same target next time.")
    if any(r.pain for r in results):
        return Step(state, "pain", f"{name}: stopped for pain. It stays out of your sessions until you say it's fine.")

    lo, hi = lad.range_for(state.level)
    regular = results[:-1] if tested else results
    test = results[-1].reps if tested else None
    best = test if test is not None else max(r.reps for r in results)
    missed = sum(1 for r in regular if r.reps < state.target)
    maxed = sum(1 for r in regular if r.effort == Effort.MAX)
    hard = sum(1 for r in regular if r.effort == Effort.HARD)

    if best < lo:
        below = state.below_range + 1
        easier = previous_usable(lad, state.level, available)
        if below >= BELOW_RANGE_SESSIONS and easier is not None:
            elo, ehi = lad.range_for(easier)
            new = ExerciseState(state.ladder, easier, (elo + ehi) // 2)
            return Step(new, "level_down", f"{name} stayed below {lo} twice, so next time it's {_target(new)}.")
        new = replace(state, target=lo, below_range=below)
        return Step(new, "hold", f"{name}: below {lo} this time. Another session like this moves you to an easier version.")

    state = replace(state, below_range=0)
    spare = LEVEL_UP_SPARE * lad.step if tested else 0
    if state.target >= hi and missed == 0 and maxed == 0 and best >= hi + spare:
        harder = next_usable(lad, state.level, available)
        if harder is not None:
            new = ExerciseState(state.ladder, harder, lad.range_for(harder)[0])
            return Step(new, "level_up", f"Top of the range on {name}: next time it's {_target(new)}.")
        return Step(state, "hold", f"{name}: top of the range on the hardest version here. Slow the lowering to 4 seconds to keep it hard.")

    if missed >= 2 or maxed >= 2:
        new = replace(state, target=max(lo, state.target - lad.step))
        return Step(new, "down_reps", f"{name}: a tough one, so next time it's {_target(new)}.")
    if missed or maxed or hard:
        return Step(state, "hold", f"{name}: right at the effort we want. Same target next time.")

    stepped = state.target + lad.step
    caught_up = best - CATCH_UP_MARGIN * lad.step if test is not None else stepped
    new_target = min(hi, max(stepped, caught_up))
    new = replace(state, target=new_target)
    decision = "catch_up" if new_target > stepped else "up_reps"
    return Step(new, decision, f"{name}: all sets felt good, so next time it's {_target(new)}.")


def _target(state: ExerciseState) -> str:
    lad = ladder(state.ladder)
    return f"{lad.at(state.level).name.lower()}, {describe_target(lad, state.level, state.target)}"


@dataclass(frozen=True)
class SessionWeek:
    sessions_done: int
    sets_planned: int
    sets_done: int
    regular_sets: int  # sets that weren't test sets
    maxed_sets: int  # regular sets rated Max
    avg_soreness: float | None  # 1-5, from session check-ins
    most_muscle_sets: float  # the highest weekly sets any major muscle got
    sessions_full: bool  # every session already used its whole time


@dataclass(frozen=True)
class VolumeReview:
    step: int
    decision: str  # up, down, hold, at_ceiling, not_enough_data
    note: str


def review_volume(week: SessionWeek, step: int) -> VolumeReview:
    if week.sessions_done < 2 or week.sets_planned == 0:
        return VolumeReview(step, "not_enough_data", "Fewer than 2 sessions last week, so the plan stays the same.")
    done = week.sets_done / week.sets_planned
    maxed = week.maxed_sets / week.regular_sets if week.regular_sets else 0.0
    sore = week.avg_soreness is not None and week.avg_soreness >= 4
    summary = f"{round(done * 100)}% of sets done"

    if done < 0.7 or maxed > 0.25:
        if step > MIN_STEP:
            return VolumeReview(step - 1, "down", f"One set fewer per exercise after a tough week ({summary}).")
        return VolumeReview(step, "hold", f"Holding steady after a tough week ({summary}); this is already the lightest plan.")
    if done >= 0.9 and maxed <= 0.1 and not sore:
        if step >= MAX_STEP or week.most_muscle_sets >= MAX_WEEKLY_SETS:
            return VolumeReview(step, "at_ceiling", f"A strong week ({summary}), and you're at the most sets this plan uses.")
        if week.sessions_full:
            return VolumeReview(
                step,
                "at_ceiling",
                f"A strong week ({summary}). Your sessions are full, so longer sessions or another day would add sets.",
            )
        return VolumeReview(step + 1, "up", f"One more set on your exercises after a strong week ({summary}).")
    if sore:
        return VolumeReview(step, "hold", f"Holding steady: you reported a lot of soreness ({summary}).")
    return VolumeReview(step, "hold", f"Holding steady ({summary}).")


class CircuitRating(StrEnum):
    EASY = "easy"
    GOOD = "good"
    HARD = "hard"
    TOO_HARD = "too_hard"


def after_circuit(level: int, rating: CircuitRating, previous: CircuitRating | None, finished: bool) -> tuple[int, str]:
    top = len(CIRCUIT_LEVELS)
    if not finished or rating == CircuitRating.TOO_HARD:
        return max(1, level - 1), "Next circuit is a step easier."
    if rating == CircuitRating.EASY or (rating == CircuitRating.GOOD and previous == CircuitRating.GOOD):
        if level < top:
            return level + 1, "Next circuit is a step harder."
        return level, "You're at the hardest circuit. Switch to the high-impact moves for more."
    return level, "Same circuit level next time."
