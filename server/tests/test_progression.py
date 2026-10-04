import datetime as dt

from engine.progression import Progression, WeekStats, review_week, week_start

# An intermediate user with a 20-rep max: 7 sets of 9 before progression, room for 8 sets.
LIMITS = dict(base_sets=7, set_limit=8, base_reps=9, max_reps=20)
STRONG = WeekStats(training_days=5, sets_planned=30, sets_done=29, hard_sets=1)  # 97%, 1 in 29 hard
ROUGH = WeekStats(training_days=5, sets_planned=30, sets_done=18, hard_sets=2)  # 60%


def test_week_start_is_monday():
    assert week_start(dt.date(2026, 10, 4)) == dt.date(2026, 9, 28)  # Sunday -> Monday before
    assert week_start(dt.date(2026, 10, 5)) == dt.date(2026, 10, 5)


def test_strong_week_adds_a_set_first():
    review = review_week(STRONG, Progression(), **LIMITS)
    assert review.decision == "up_sets"
    assert review.progression == Progression(1, 0, "sets")
    assert review.note == "+1 set a day after a strong week (97% done, 1 hard set)."


def test_steps_alternate_between_sets_and_reps():
    review = review_week(STRONG, Progression(1, 0, "sets"), **LIMITS)
    assert review.decision == "up_reps" and review.progression == Progression(1, 1, "reps")


def test_sets_stop_at_the_window_and_prompt_limit():
    # 7 + 1 = 8 sets already, the limit: reps grow instead.
    review = review_week(STRONG, Progression(1, 1, "reps"), **LIMITS)
    assert review.decision == "up_reps" and review.progression.extra_reps == 2


def test_reps_never_pass_60_percent_of_max():
    # Ceiling is 12 reps (60% of 20); 9 + 3 = 12 already, and sets are full.
    review = review_week(STRONG, Progression(1, 3, "reps"), **LIMITS)
    assert review.decision == "at_ceiling"
    assert review.progression == Progression(1, 3, "reps")
    assert "new max test" in review.note


def test_too_many_hard_sets_blocks_a_step_up():
    hard_week = WeekStats(training_days=5, sets_planned=30, sets_done=29, hard_sets=4)  # 14% hard
    assert review_week(hard_week, Progression(), **LIMITS).decision == "hold"


def test_rough_week_removes_reps_before_sets():
    assert review_week(ROUGH, Progression(1, 2, "reps"), **LIMITS).progression == Progression(1, 1, "reps")
    down = review_week(ROUGH, Progression(1, 0, "sets"), **LIMITS)
    assert down.decision == "down_sets" and down.progression == Progression(0, 0, "sets")
    assert down.note == "1 set fewer a day after a tough week (60% done, 2 hard sets)."


def test_mostly_hard_week_steps_down_even_if_completed():
    grinding = WeekStats(training_days=5, sets_planned=30, sets_done=30, hard_sets=9)  # 30% hard
    assert review_week(grinding, Progression(), **LIMITS).decision == "down_sets"


def test_lightest_plan_cannot_go_lower():
    tiny = dict(base_sets=2, set_limit=8, base_reps=1, max_reps=2)
    review = review_week(ROUGH, Progression(), **tiny)
    assert review.decision == "hold" and "lightest" in review.note


def test_too_few_training_days_changes_nothing():
    review = review_week(WeekStats(2, 12, 12, 0), Progression(1, 0, "sets"), **LIMITS)
    assert review.decision == "not_enough_data" and review.progression == Progression(1, 0, "sets")


def test_a_middling_week_holds():
    middling = WeekStats(training_days=5, sets_planned=30, sets_done=24, hard_sets=1)  # 80%
    assert review_week(middling, Progression(), **LIMITS).decision == "hold"
