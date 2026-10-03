"""Streak of days on plan.

A day is on plan when the user did at least one set, had a planned rest day, or
stopped because of pain. Stopping for pain must never cost a streak.

The first missed day in each week (Monday to Sunday) is covered by a rest pass: the
streak carries on without growing. Research on Duolingo's streak freeze found this
kind of slack keeps people going. Today only counts once it's on plan, and not having
trained yet today never breaks the streak.
"""

import datetime as dt
from dataclasses import dataclass, field


@dataclass(frozen=True)
class DayRecord:
    day: dt.date
    plan_kind: str | None  # training, mobility, window_passed; None without a plan
    sets_done: int  # sets with reps done, skipped sets excluded
    stopped_for_pain: bool


@dataclass(frozen=True)
class Streak:
    current: int
    best: int
    today_on_plan: bool
    rest_pass_available: bool  # this week's pass is still unused
    rest_pass_days: list[dt.date] = field(default_factory=list)


def on_plan(record: DayRecord | None) -> bool:
    if record is None:
        return False
    return record.sets_done > 0 or record.plan_kind == "mobility" or record.stopped_for_pain


def _week(day: dt.date) -> tuple[int, int]:
    year, week, _ = day.isocalendar()
    return year, week


def compute_streak(records: list[DayRecord], today: dt.date) -> Streak:
    by_day = {r.day: r for r in records}
    past = [d for d in by_day if d < today]
    if not past:
        today_on = on_plan(by_day.get(today))
        return Streak(int(today_on), int(today_on), today_on, True)

    streak = best = 0
    pass_week: tuple[int, int] | None = None
    pass_days: list[dt.date] = []
    day = min(past)  # history starts at the first day the user checked in
    while day < today:
        if on_plan(by_day.get(day)):
            streak += 1
        elif streak > 0 and pass_week != _week(day):
            pass_week = _week(day)  # covered: the streak survives but doesn't grow
            pass_days.append(day)
        else:
            streak = 0
        best = max(best, streak)
        day += dt.timedelta(days=1)

    today_on = on_plan(by_day.get(today))
    current = streak + int(today_on)
    return Streak(
        current=current,
        best=max(best, current),
        today_on_plan=today_on,
        rest_pass_available=pass_week != _week(today),
        rest_pass_days=pass_days,
    )
