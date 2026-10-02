from collections import defaultdict
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class LogRow:
    day: date
    done_reps: int
    rating: str


@dataclass(frozen=True)
class DaySummary:
    day: date
    sets_done: int
    reps_done: int
    hard_sets: int


def daily_summary(logs: list[LogRow]) -> list[DaySummary]:
    """Per-day totals. Skipped sets don't count as done; pain sets count if reps were done."""
    sets: dict[date, int] = defaultdict(int)
    reps: dict[date, int] = defaultdict(int)
    hard: dict[date, int] = defaultdict(int)
    for row in logs:
        if row.rating != "skipped" and row.done_reps > 0:
            sets[row.day] += 1
            reps[row.day] += row.done_reps
        if row.rating == "hard":
            hard[row.day] += 1
    days = sorted({row.day for row in logs})
    return [DaySummary(d, sets[d], reps[d], hard[d]) for d in days]
