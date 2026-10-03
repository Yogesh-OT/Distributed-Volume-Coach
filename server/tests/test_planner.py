from dataclasses import replace

from hypothesis import given, settings
from hypothesis import strategies as st

from engine.common import SET_CAP, experience_for, round_half_up, to_hhmm, to_minutes
from engine.plan import PlanKind
from engine.planner import CHECKIN_LEAD_MIN, PlannerInput, build_plan
from engine.readiness import readiness

SAMPLE = PlannerInput(
    date="2026-10-05",
    exercise="pushup",
    checkin_time="07:40",
    window_start="09:00",
    window_end="19:00",
    quiet_hours=("21:30", "07:00"),
    prompt_limit=8,
    training_months=12,  # intermediate
    max_reps=20,
    sleep_quality=4,
    soreness=2,
    energy=4,
    seed="user-1:2026-10-05",
)


def _gaps(plan):
    minutes = [to_minutes(s.at) for s in plan.sets]
    return [b - a for a, b in zip(minutes, minutes[1:])]


def test_sample_day_matches_the_architecture_page():
    plan = build_plan(SAMPLE)

    assert plan.kind is PlanKind.TRAINING
    assert plan.readiness == 0.75
    assert len(plan.sets) == 6
    assert {s.target_reps for s in plan.sets} == {9}
    assert plan.reason == "Good sleep, good energy and low soreness: 6 sets of 9 (45% of your 20-rep max)."
    assert all("09:00" <= s.at <= "19:00" for s in plan.sets)
    assert min(_gaps(plan)) >= 45


def test_same_seed_gives_the_same_plan():
    assert build_plan(SAMPLE) == build_plan(SAMPLE)


def test_halves_round_up_like_kotlin():
    # Beginner cap 5, readiness 0.75: 5 * 0.9 = 4.5 sets. Python's round() would give 4.
    plan = build_plan(replace(SAMPLE, training_months=3))
    assert len(plan.sets) == 5
    assert round_half_up(4.5) == 5
    assert round_half_up(0.45 * 20) == 9


def test_low_readiness_gives_a_mobility_day():
    plan = build_plan(replace(SAMPLE, sleep_quality=1, soreness=5, energy=1))
    assert plan.kind is PlanKind.MOBILITY
    assert plan.sets == []
    assert plan.reason.startswith("Poor sleep, low energy and high soreness")


def test_readiness_of_exactly_a_quarter_still_trains():
    assert readiness(2, 4, 2) == 0.25
    assert build_plan(replace(SAMPLE, sleep_quality=2, soreness=4, energy=2)).kind is PlanKind.TRAINING


def test_late_check_in_fits_fewer_sets_and_says_why():
    plan = build_plan(replace(SAMPLE, checkin_time="17:30"))
    assert len(plan.sets) == 1
    assert plan.sets[0].at >= "17:45"
    assert ": 1 set of 9 (" in plan.reason
    assert plan.reason.endswith("5 fewer than usual because of the late check-in.")


def test_check_in_after_the_window_gives_no_sets():
    plan = build_plan(replace(SAMPLE, checkin_time="19:00"))
    assert plan.kind is PlanKind.WINDOW_PASSED
    assert plan.sets == []


def test_policy_carries_the_window_and_quiet_hours():
    policy = build_plan(SAMPLE).to_dict()["policy"]
    assert policy["window_end"] == "19:00"
    assert policy["quiet_hours"] == ["21:30", "07:00"]
    assert policy["on_hard"] == {"scale_remaining_reps": 0.8, "delay_remaining_min": 30}


@st.composite
def planner_inputs(draw):
    start = draw(st.integers(5 * 60, 12 * 60))
    end = draw(st.integers(start + 60, min(start + 900, 23 * 60 + 59)))
    checkin = draw(st.integers(4 * 60, 20 * 60))
    return replace(
        SAMPLE,
        checkin_time=to_hhmm(checkin),
        window_start=to_hhmm(start),
        window_end=to_hhmm(end),
        prompt_limit=draw(st.integers(1, 12)),
        training_months=draw(st.integers(0, 60)),
        max_reps=draw(st.integers(1, 100)),
        sleep_quality=draw(st.integers(1, 5)),
        soreness=draw(st.integers(1, 5)),
        energy=draw(st.integers(1, 5)),
        seed=draw(st.text(max_size=12)),
    )


@settings(max_examples=2000, deadline=None)
@given(planner_inputs())
def test_every_plan_respects_the_window_gaps_and_caps(inp):
    plan = build_plan(inp)
    if plan.kind is not PlanKind.TRAINING:
        assert plan.sets == []
        return

    earliest = max(to_minutes(inp.window_start), to_minutes(inp.checkin_time) + CHECKIN_LEAD_MIN)
    times = [to_minutes(s.at) for s in plan.sets]
    assert 1 <= len(plan.sets) <= SET_CAP[experience_for(inp.training_months)]
    assert times == sorted(times)
    assert all(earliest <= t <= to_minutes(inp.window_end) for t in times)
    assert all(gap >= 45 for gap in _gaps(plan))
    assert all(s.target_reps >= 1 for s in plan.sets)
    assert [s.ref for s in plan.sets] == [f"s{i + 1}" for i in range(len(plan.sets))]
