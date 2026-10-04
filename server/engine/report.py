"""Numbers for the report page. Pure functions; the API gathers the rows."""

import datetime as dt
from collections.abc import Iterable

from .exercises import Muscle, ladder


def logged_muscle_sets(ladders: Iterable[str]) -> dict[Muscle, float]:
    """Sets per muscle from logged sets (one ladder key per set), indirect work as half."""
    totals = {m: 0.0 for m in Muscle}
    for key in ladders:
        for muscle, weight in ladder(key).muscles.items():
            totals[muscle] += weight
    return totals


def week_streak(done_by_week: dict[dt.date, int], target: int, this_week: dt.date) -> tuple[int, int]:
    """(current, best) runs of weeks with at least `target` sessions. Weeks are keyed by
    their Monday. The current week counts once it's met, and never breaks the run."""
    if target <= 0:
        return 0, 0
    met = {week for week, done in done_by_week.items() if done >= target}
    best = run = 0
    if met:
        week = min(met)
        while week <= this_week:
            run = run + 1 if week in met else 0
            best = max(best, run)
            week += dt.timedelta(days=7)
    current = 0
    week = this_week if this_week in met else this_week - dt.timedelta(days=7)
    while week in met:
        current += 1
        week -= dt.timedelta(days=7)
    return current, best


def weekly_weight_change(weights: list[tuple[dt.date, float]], today: dt.date) -> float | None:
    """Percent change between the average of the last 7 days and the 7 days before,
    or None without a weigh-in in both."""
    recent = [kg for day, kg in weights if 0 <= (today - day).days < 7]
    before = [kg for day, kg in weights if 7 <= (today - day).days < 14]
    if not recent or not before:
        return None
    a, b = sum(recent) / len(recent), sum(before) / len(before)
    return round((a - b) / b * 100, 2)
