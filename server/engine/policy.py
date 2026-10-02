"""In-day rules: how logged sets change the rest of today.

This is the reference implementation. The phone runs a Kotlin port of the same
rules offline, and both are checked against shared/policy_vectors.json.

Rules, applied to each log in time order:
- Sets earlier in the plan that were never logged become "missed".
- Pain: stop this exercise for today.
- Hard: scale the remaining reps and push the remaining sets later. Reaching the
  hard-set limit ends the day.
- Every remaining set stays at least min_gap after the last log and after the set
  before it. Sets pushed past the window end are dropped.
"""

from dataclasses import dataclass
from enum import StrEnum

from .common import round_half_up, to_hhmm, to_minutes
from .plan import PlannedSet, Policy


class Rating(StrEnum):
    EASY = "easy"
    SOLID = "solid"
    HARD = "hard"  # 0-1 reps left in the tank
    PAIN = "pain"
    SKIPPED = "skipped"


class SetStatus(StrEnum):
    LOGGED = "logged"
    MISSED = "missed"
    PENDING = "pending"
    DROPPED = "dropped"


class DayStatus(StrEnum):
    ACTIVE = "active"
    COMPLETE = "complete"
    ENDED_HARD = "ended_hard"
    STOPPED_PAIN = "stopped_pain"


@dataclass(frozen=True)
class LoggedSet:
    ref: str
    rating: Rating
    at: str  # local HH:MM when it was logged


@dataclass(frozen=True)
class SetState:
    ref: str
    at: str
    target_reps: int
    status: SetStatus
    rating: Rating | None = None


@dataclass(frozen=True)
class DayState:
    sets: list[SetState]
    status: DayStatus
    hard_sets: int


@dataclass
class _Working:
    ref: str
    at: int
    target: int
    status: SetStatus = SetStatus.PENDING
    rating: Rating | None = None


def apply_logs(sets: list[PlannedSet], policy: Policy, logs: list[LoggedSet]) -> DayState:
    work = [_Working(s.ref, to_minutes(s.at), s.target_reps) for s in sets]
    index = {w.ref: i for i, w in enumerate(work)}
    window_end = to_minutes(policy.window_end)
    status = DayStatus.ACTIVE
    hard = 0

    # Stable sort: logs at the same minute keep their original order.
    for log in sorted(logs, key=lambda entry: to_minutes(entry.at)):
        i = index.get(log.ref)
        if status is not DayStatus.ACTIVE or i is None or work[i].status is not SetStatus.PENDING:
            continue  # unknown set, already logged, or the day is over

        work[i].status, work[i].rating = SetStatus.LOGGED, log.rating
        for earlier in work[:i]:
            if earlier.status is SetStatus.PENDING:
                earlier.status = SetStatus.MISSED
        remaining = [w for w in work[i + 1 :] if w.status is SetStatus.PENDING]

        if log.rating is Rating.PAIN:
            status = DayStatus.STOPPED_PAIN
            _drop(remaining)
            continue
        if log.rating is Rating.HARD:
            hard += 1
            if hard >= policy.end_day_after_hard_sets:
                status = DayStatus.ENDED_HARD
                _drop(remaining)
                continue
            for w in remaining:
                w.target = max(1, round_half_up(w.target * policy.scale_remaining_reps))
                w.at += policy.delay_remaining_min

        previous = to_minutes(log.at)
        for w in remaining:
            w.at = max(w.at, previous + policy.min_gap_min)
            previous = w.at
            if w.at > window_end:
                w.status = SetStatus.DROPPED

    if status is DayStatus.ACTIVE and not any(w.status is SetStatus.PENDING for w in work) and logs:
        status = DayStatus.COMPLETE

    return DayState(
        sets=[
            # Sets pushed past midnight are already dropped; clamp so they still format.
            SetState(w.ref, to_hhmm(min(w.at, 24 * 60 - 1)), w.target, w.status, w.rating)
            for w in work
        ],
        status=status,
        hard_sets=hard,
    )


def _drop(sets: list[_Working]) -> None:
    for w in sets:
        w.status = SetStatus.DROPPED
