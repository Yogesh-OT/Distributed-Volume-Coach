import datetime as dt

import pytest

from engine.levels import LEVELS, level, suggest
from engine.streak import DayRecord, compute_streak

# Saturday 3 Oct 2026. Its ISO week runs Monday 28 Sep to Sunday 4 Oct.
TODAY = dt.date(2026, 10, 3)


def day(offset: int) -> dt.date:
    return TODAY + dt.timedelta(days=offset)


def trained(offset: int) -> DayRecord:
    return DayRecord(day(offset), "training", 3, False)


def missed(offset: int, kind: str | None = "training") -> DayRecord:
    return DayRecord(day(offset), kind, 0, False)


def test_no_history():
    s = compute_streak([], TODAY)
    assert (s.current, s.best, s.today_on_plan, s.rest_pass_available) == (0, 0, False, True)


def test_today_not_done_yet_keeps_the_streak_alive():
    s = compute_streak([trained(-3), trained(-2), trained(-1)], TODAY)
    assert (s.current, s.today_on_plan) == (3, False)


def test_today_counts_once_on_plan():
    s = compute_streak([trained(-2), trained(-1), trained(0)], TODAY)
    assert (s.current, s.best, s.today_on_plan) == (3, 3, True)


def test_rest_days_and_pain_stops_count():
    records = [
        trained(-3),
        DayRecord(day(-2), "mobility", 0, False),  # planned rest
        DayRecord(day(-1), "training", 0, True),  # stopped for pain before finishing a rep
    ]
    assert compute_streak(records, TODAY).current == 3


@pytest.mark.parametrize("miss", [missed(-2), missed(-2, "window_passed"), missed(-2, None)])
def test_first_miss_in_a_week_is_covered_by_a_rest_pass(miss):
    s = compute_streak([trained(-4), trained(-3), miss, trained(-1)], TODAY)
    assert s.current == 3  # the covered day doesn't add to the streak
    assert s.rest_pass_days == [day(-2)]
    assert not s.rest_pass_available  # this week's pass is used


def test_second_miss_in_the_same_week_resets():
    s = compute_streak([trained(-5), missed(-4), trained(-3), missed(-2), trained(-1)], TODAY)
    assert s.current == 1
    assert s.best == 2  # day -5 plus day -3, with day -4 covered


def test_misses_in_different_weeks_are_both_covered():
    # Day -6 is Sunday 27 Sep (previous ISO week); day -2 is Thursday 1 Oct.
    records = [trained(-7), missed(-6), trained(-5), trained(-4), trained(-3), missed(-2), trained(-1)]
    s = compute_streak(records, TODAY)
    assert s.current == 5
    assert s.rest_pass_days == [day(-6), day(-2)]


def test_a_miss_with_no_streak_does_not_use_the_pass():
    s = compute_streak([missed(-3), trained(-2), trained(-1)], TODAY)
    assert s.current == 2
    assert s.rest_pass_days == [] and s.rest_pass_available


def test_best_survives_a_reset():
    records = [trained(-6), trained(-5), trained(-4), missed(-3), missed(-2), trained(-1)]
    s = compute_streak(records, TODAY)
    assert (s.current, s.best) == (1, 3)


def test_levels_are_ordered_easiest_first():
    assert [lv.key for lv in LEVELS] == ["wall", "incline", "knee", "full", "decline"]
    assert level(4).plural == "push-ups"
    with pytest.raises(ValueError):
        level(6)


def test_level_suggestions():
    up = suggest(3, 22)
    assert up.direction == "up" and up.level == 4 and "push-ups" in up.message
    down = suggest(4, 3)
    assert down.direction == "down" and down.level == 3 and "knee push-ups" in down.message
    assert suggest(4, 12) is None
    assert suggest(5, 40) is None  # nothing harder to move to
    assert suggest(1, 2) is None  # nothing easier to move to
