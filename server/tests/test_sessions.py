import itertools

import pytest

from engine.exercises import (
    EVERYDAY,
    LADDERS,
    MAJOR_MUSCLES,
    ExerciseState,
    Muscle,
    Need,
    Unit,
    ladder,
    starting_state,
)
from engine.levels import LEVELS
from engine.session_progression import (
    CircuitRating,
    Effort,
    SessionWeek,
    SetResult,
    after_circuit,
    after_session,
    review_volume,
)
from engine.sessions import (
    CIRCUIT,
    DAYS_PER_WEEK,
    MAIN_LADDERS,
    MAX_STEP,
    MIN_STEP,
    SESSION_LENGTHS,
    TEMPLATES,
    Goal,
    SessionInput,
    WeekSlot,
    build_session,
    week_plan,
    weekly_sets,
)

STATES = {key: starting_state(key, 2) for key in LADDERS}


def week(goal, days, minutes, step=0, states=STATES, **kw):
    return [
        build_session(SessionInput(goal, slot, minutes, states, volume_step=step, seed=str(i), **kw))
        for i, slot in enumerate(week_plan(goal, days))
    ]


# --- the exercise library ---


def test_ladders_are_numbered_and_sane():
    for lad in LADDERS.values():
        assert [ex.level for ex in lad.exercises] == list(range(1, len(lad.exercises) + 1))
        for ex in lad.exercises:
            lo, hi = lad.range_for(ex.level)
            assert 0 < lo < hi and ex.cue
        assert max(lad.muscles.values()) == 1


def test_push_ladder_matches_the_spread_out_mode_levels():
    for lvl in LEVELS:
        assert ladder("push").at(lvl.number).key == f"pushup_{lvl.key}"


def test_every_template_uses_known_ladders():
    for pairs in TEMPLATES.values():
        for pair in pairs:
            assert 1 <= len(pair) <= 2 and all(k in LADDERS for k in pair)


def test_starting_from_a_max_test():
    assert starting_state("push", 4, max_reps=20) == ExerciseState("push", 4, 14)  # 70% of 20
    assert starting_state("push", 4, max_reps=6) == ExerciseState("push", 4, 6)  # bottom of the range
    # 70% of 25 is past the top of the range: start the next level at the bottom.
    assert starting_state("push", 4, max_reps=25) == ExerciseState("push", 5, 6)


def test_missing_furniture_falls_back_to_an_easier_version():
    no_table = EVERYDAY  # doorway, chair, wall, smooth floor
    assert starting_state("row", 3, no_table).level == 1  # doorway row
    assert starting_state("row", 3, EVERYDAY | {Need.TABLE}).level == 3


# --- building the week and the session ---


def test_week_plans():
    assert [s.template for s in week_plan(Goal.MUSCLE, 3)] == ["A", "B", "C"]
    assert [s.template for s in week_plan(Goal.MUSCLE, 4)] == ["U1", "L1", "U2", "L2"]
    assert [s.template for s in week_plan(Goal.FIT, 3)] == ["A", CIRCUIT, "B"]
    assert all(s.finisher for s in week_plan(Goal.FIT, 2))
    with pytest.raises(ValueError):
        week_plan(Goal.MUSCLE, 6)


@pytest.mark.parametrize("days,minutes", list(itertools.product(DAYS_PER_WEEK, SESSION_LENGTHS)))
def test_every_major_muscle_twice_a_week(days, minutes):
    # ACSM 2026: train every major muscle at least twice a week.
    sessions = week(Goal.MUSCLE, days, minutes)
    for muscle in MAJOR_MUSCLES:
        trained = sum(1 for s in sessions if weekly_sets([s])[muscle] > 0)
        assert trained >= 2, (muscle, [s.template for s in sessions])


def test_three_half_hour_sessions_give_about_ten_sets_per_muscle():
    sets = weekly_sets(week(Goal.MUSCLE, 3, 30))
    for muscle in (Muscle.CHEST, Muscle.BACK, Muscle.QUADS, Muscle.GLUTES):
        assert 8 <= sets[muscle] <= 12, (muscle, sets[muscle])


@pytest.mark.parametrize(
    "goal,days,minutes,step",
    list(itertools.product(Goal, DAYS_PER_WEEK, SESSION_LENGTHS, range(MIN_STEP, MAX_STEP + 1))),
)
def test_sessions_fit_the_chosen_length(goal, days, minutes, step):
    for session in week(goal, days, minutes, step):
        assert session.minutes <= minutes, (session.template, session.minutes)


@pytest.mark.parametrize("days,minutes", list(itertools.product(DAYS_PER_WEEK, SESSION_LENGTHS)))
def test_more_volume_never_drops_an_exercise(days, minutes):
    base = [{ex.ladder for ex in s.exercises} for s in week(Goal.MUSCLE, days, minutes, 0)]
    more = [{ex.ladder for ex in s.exercises} for s in week(Goal.MUSCLE, days, minutes, MAX_STEP)]
    assert all(b <= m for b, m in zip(base, more))


def test_pairs_rest_60_seconds_and_main_movements_come_first():
    session = build_session(SessionInput(Goal.MUSCLE, WeekSlot("A"), 30, STATES))
    first = session.pairs[0]
    assert [ex.ladder for ex in first] == ["push", "row"]
    assert all(ex.rest_s == 60 for ex in first) and all(ex.sets == 3 for ex in first)
    assert all(ex.test_last_set for ex in first)


def test_light_session_after_a_rough_check_in():
    session = build_session(SessionInput(Goal.MUSCLE, WeekSlot("A"), 30, STATES, readiness=0.2))
    assert session.light
    assert all(ex.ladder in MAIN_LADDERS and ex.sets == 2 and not ex.test_last_set for ex in session.exercises)
    assert session.note.startswith("A light session")


def test_below_average_check_in_trims_extras():
    normal = build_session(SessionInput(Goal.MUSCLE, WeekSlot("A"), 45, STATES))
    tired = build_session(SessionInput(Goal.MUSCLE, WeekSlot("A"), 45, STATES, readiness=0.4))
    assert tired.total_sets < normal.total_sets
    assert tired.note.startswith("One set fewer")


def test_a_pair_without_a_partner_rests_longer():
    nothing_to_row_on = frozenset({Need.WALL, Need.CHAIR, Need.SMOOTH_FLOOR})  # no doorway, no table
    session = build_session(SessionInput(Goal.MUSCLE, WeekSlot("A"), 30, STATES, available=nothing_to_row_on))
    first = session.pairs[0]
    assert [ex.ladder for ex in first] == ["push"] and first[0].rest_s == 90


def test_holds_are_in_seconds():
    plank = next(ex for ex in build_session(SessionInput(Goal.MUSCLE, WeekSlot("A"), 45, STATES)).exercises if ex.ladder == "plank")
    assert plank.unit == Unit.SECONDS and plank.target == 20


def test_circuits_default_to_low_impact():
    circuit = build_session(SessionInput(Goal.FIT, WeekSlot(CIRCUIT), 30, STATES, seed="x")).circuit
    assert circuit is not None and len(circuit.moves) == 4
    assert "Jumping jacks" not in circuit.moves and "Burpee" not in circuit.moves
    loud = build_session(SessionInput(Goal.FIT, WeekSlot(CIRCUIT), 30, STATES, seed="x", high_impact=True)).circuit
    assert loud.moves != circuit.moves


def test_finisher_only_when_there_is_time():
    short = build_session(SessionInput(Goal.FIT, WeekSlot("A", finisher=True), 20, STATES))
    longer = build_session(SessionInput(Goal.FIT, WeekSlot("A", finisher=True), 30, STATES))
    assert short.circuit is None and longer.circuit is not None and longer.circuit.rounds == 2


# --- progression after a session ---

PUSH = ExerciseState("push", 4, 10)


def sets(*reps, effort=Effort.GOOD):
    return [SetResult(r, effort) for r in reps]


def test_good_sets_add_a_rep():
    step = after_session(PUSH, sets(10, 10, 12), tested=True)
    assert step.decision == "up_reps" and step.state.target == 11
    assert step.note == "Push-up: all sets felt good, so next time it's push-up, 11 reps."


def test_targets_catch_up_to_a_strong_test_set():
    step = after_session(PUSH, sets(10, 10, 17), tested=True)
    assert step.decision == "catch_up" and step.state.target == 14  # 17 - 3


def test_a_hard_set_holds_the_target():
    results = [SetResult(10, Effort.GOOD), SetResult(10, Effort.HARD), SetResult(11)]
    assert after_session(PUSH, results, tested=True).decision == "hold"


def test_two_missed_sets_drop_a_rep():
    step = after_session(PUSH, sets(8, 9, 9), tested=True)
    assert step.decision == "down_reps" and step.state.target == 9


def test_top_of_the_range_moves_up_a_level():
    top = ExerciseState("push", 4, 15)
    step = after_session(top, sets(15, 15, 17), tested=True)
    assert step.decision == "level_up" and step.state == ExerciseState("push", 5, 6)
    # Without 2 spare reps on the test set, stay and keep working.
    assert after_session(top, sets(15, 15, 16), tested=True).decision == "up_reps"


def test_untested_exercises_move_up_at_the_top():
    nordic_ready = ExerciseState("curl", 2, 15)
    with_sofa = EVERYDAY | {Need.SOFA}
    assert after_session(nordic_ready, sets(15, 15), tested=False, available=with_sofa).decision == "level_up"
    # Nordic curls need a heavy sofa; without one, stay on the single-leg curl.
    assert after_session(nordic_ready, sets(15, 15), tested=False).decision == "hold"


def test_twice_below_the_range_moves_down_a_level():
    first = after_session(PUSH, sets(5, 4, 4), tested=True)
    assert first.decision == "hold" and first.state.below_range == 1
    second = after_session(first.state, sets(5, 4, 4), tested=True)
    assert second.decision == "level_down" and second.state == ExerciseState("push", 3, 10)


def test_level_up_skips_versions_you_cant_do_at_home():
    # Decline push-ups need a chair; without one, full push-ups go straight to archer.
    no_chair = frozenset({Need.WALL})
    step = after_session(ExerciseState("push", 4, 15), sets(15, 15, 18), tested=True, available=no_chair)
    assert step.state.level == 6


def test_pain_and_skips():
    assert after_session(PUSH, [SetResult(10), SetResult(3, pain=True)], tested=True).decision == "pain"
    assert after_session(PUSH, [], tested=True).decision == "skipped"


def test_holds_grow_by_five_seconds():
    plank = ExerciseState("plank", 2, 30)
    assert after_session(plank, sets(30, 30, 40), tested=True).state.target == 35


# --- the weekly volume review ---

STRONG = SessionWeek(3, 50, 48, 36, 1, 2.5, 10, sessions_full=False)


def test_strong_week_adds_a_set():
    review = review_volume(STRONG, 0)
    assert review.decision == "up" and review.step == 1


def test_full_sessions_cant_grow():
    full = SessionWeek(3, 50, 48, 36, 1, 2.5, 10, sessions_full=True)
    review = review_volume(full, 0)
    assert review.decision == "at_ceiling" and "longer sessions" in review.note


def test_twenty_sets_is_the_ceiling():
    busy = SessionWeek(3, 50, 48, 36, 1, 2.5, 20, sessions_full=False)
    assert review_volume(busy, 1).decision == "at_ceiling"


def test_tough_week_removes_a_set_down_to_the_floor():
    tough = SessionWeek(3, 50, 30, 36, 2, 3.0, 10, sessions_full=False)
    assert review_volume(tough, 0).step == -1
    assert review_volume(tough, MIN_STEP).decision == "hold"


def test_high_soreness_blocks_a_step_up():
    sore = SessionWeek(3, 50, 48, 36, 1, 4.2, 10, sessions_full=False)
    assert review_volume(sore, 0).decision == "hold"


def test_one_session_is_too_little_to_judge():
    assert review_volume(SessionWeek(1, 17, 17, 13, 0, None, 4, False), 0).decision == "not_enough_data"


# --- circuits ---


def test_circuit_levels():
    assert after_circuit(2, CircuitRating.EASY, None, True)[0] == 3
    assert after_circuit(2, CircuitRating.GOOD, CircuitRating.GOOD, True)[0] == 3
    assert after_circuit(2, CircuitRating.GOOD, None, True)[0] == 2
    assert after_circuit(2, CircuitRating.HARD, None, False)[0] == 1
    assert after_circuit(1, CircuitRating.TOO_HARD, None, True)[0] == 1


# --- coming back, starting levels, rotation and the report ---

import datetime as dt  # noqa: E402

from engine.common import Experience  # noqa: E402
from engine.report import logged_muscle_sets, week_streak, weekly_weight_change  # noqa: E402
from engine.session_progression import after_break  # noqa: E402
from engine.sessions import initial_states, rotation  # noqa: E402


def test_coming_back_after_a_break():
    assert after_break(PUSH, 10) == PUSH
    assert after_break(PUSH, 15).target == 7  # 10 - 3
    assert after_break(PUSH, 30) == ExerciseState("push", 3, 10)  # one level easier, mid-range


def test_initial_states_use_the_push_up_max():
    states = initial_states(Experience.BEGINNER, EVERYDAY, push_max=20, push_level=4)
    assert states["push"] == ExerciseState("push", 4, 14)
    assert states["row"].level == 1  # no table: doorway rows
    assert set(states) == set(LADDERS)


def test_rotation_never_skips_a_workout():
    assert [rotation(Goal.MUSCLE, 3, n).template for n in range(5)] == ["A", "B", "C", "A", "B"]


def test_paused_exercises_are_left_out():
    session = build_session(SessionInput(Goal.MUSCLE, WeekSlot("A"), 30, STATES, paused=frozenset({"row"})))
    assert "row" not in {ex.ladder for ex in session.exercises}


def test_report_numbers():
    sets = logged_muscle_sets(["push", "push", "row"])
    assert sets[Muscle.CHEST] == 2 and sets[Muscle.TRICEPS] == 1 and sets[Muscle.BACK] == 1
    mon = dt.date(2026, 10, 5)
    weeks = {mon - dt.timedelta(days=7 * i): n for i, n in enumerate([1, 3, 3, 2, 3])}
    assert week_streak(weeks, 3, mon) == (2, 2)  # this week (1) isn't met yet and doesn't break it
    weights = [(mon - dt.timedelta(days=d), kg) for d, kg in [(1, 79.0), (3, 79.0), (9, 80.0)]]
    assert weekly_weight_change(weights, mon) == -1.25
    assert weekly_weight_change(weights[:2], mon) is None
