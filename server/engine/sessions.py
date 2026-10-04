"""Session mode: which workouts make up the week, and what today's session holds.

The rules come from docs/training-research.md:
- every major muscle at least twice a week (ACSM 2026)
- exercises in pairs that use different muscles, 60 s between sets (Singer 2024,
  Iversen 2021), so each muscle rests about 2.5-3 minutes
- about 10 sets per muscle a week to start, more as the weekly review allows
- the last set of each exercise goes as far as good form allows, as a test

Main movements (push, row, squat, lunge, hinge, leg curl, pike) get 3 sets and extras 2 at
the starting volume. Earlier pairs in a template are kept first when time is short.
"""

import hashlib
import math
from dataclasses import asdict, dataclass, replace
from enum import StrEnum

from .common import Experience

from .exercises import (
    CARDIO_MOVES,
    CIRCUIT_LEVELS,
    EVERYDAY,
    ExerciseState,
    Muscle,
    LADDERS,
    Need,
    Unit,
    ladder,
    nearest_usable,
    starting_state,
)


class Goal(StrEnum):
    MUSCLE = "muscle"  # build muscle
    FIT = "fit"  # get fit / lose fat


PAIR_REST_S = 60
SINGLE_REST_S = 90  # an exercise without a partner rests on its own
WARMUP_S = 180
SESSION_LENGTHS = (20, 30, 45)
DAYS_PER_WEEK = (2, 3, 4)
MIN_STEP, MAX_STEP = -1, 2  # volume steps from the weekly review
LIGHT_BELOW = 0.25  # readiness below this: a light session
FEWER_EXTRAS_BELOW = 0.5  # readiness below this: one set fewer on the extra pairs
FINISHER_FROM_MINUTES = 30  # shorter sessions have no room for a finisher circuit
# Compound movements for the big muscles get more sets and are kept on light days.
MAIN_LADDERS = frozenset({"push", "row", "squat", "lunge", "hinge", "curl", "pike"})

TEMPLATES: dict[str, tuple[tuple[str, ...], ...]] = {
    # Full body, for 2 or 3 days a week.
    "A": (("push", "row"), ("squat", "crunch"), ("hinge", "calves"), ("pike", "plank")),
    "B": (("push", "row"), ("squat", "plank"), ("curl", "calves"), ("triceps", "crunch")),
    "C": (("push", "row"), ("squat", "side_plank"), ("hinge", "calves"), ("pike", "crunch")),
    # Upper and lower body, for 4 days a week. Rows appear twice: the back gets no
    # other direct work without a pull-up bar.
    "U1": (("push", "row"), ("pike", "row"), ("triceps", "plank")),
    "L1": (("squat", "crunch"), ("hinge", "calves"), ("curl", "side_plank")),
    "U2": (("pike", "row"), ("push", "row"), ("triceps", "crunch")),
    "L2": (("squat", "plank"), ("lunge", "calves"), ("curl", "crunch")),
}
TEMPLATE_TITLES = {
    "A": "Full body A",
    "B": "Full body B",
    "C": "Full body C",
    "U1": "Upper body 1",
    "L1": "Lower body 1",
    "U2": "Upper body 2",
    "L2": "Lower body 2",
    "circuit": "Fitness circuit",
}
CIRCUIT = "circuit"

@dataclass(frozen=True)
class WeekSlot:
    template: str  # a TEMPLATES key or "circuit"
    finisher: bool = False  # a short circuit after the strength work


def week_plan(goal: Goal, days: int) -> tuple[WeekSlot, ...]:
    if days not in DAYS_PER_WEEK:
        raise ValueError(f"days must be one of {DAYS_PER_WEEK}, got {days}")
    if goal == Goal.MUSCLE:
        keys = {2: ("A", "B"), 3: ("A", "B", "C"), 4: ("U1", "L1", "U2", "L2")}[days]
        return tuple(WeekSlot(k) for k in keys)
    # Get fit: strength keeps muscle, circuits add fitness (Lafontant 2025, Schumann 2022).
    if days == 2:
        return (WeekSlot("A", finisher=True), WeekSlot("B", finisher=True))
    if days == 3:
        return (WeekSlot("A"), WeekSlot(CIRCUIT), WeekSlot("B"))
    return (WeekSlot("A"), WeekSlot(CIRCUIT), WeekSlot("B"), WeekSlot(CIRCUIT))


@dataclass(frozen=True)
class PlannedExercise:
    ladder: str
    key: str
    name: str
    level: int
    sets: int
    target: int
    unit: Unit
    each_side: bool
    rep_range: tuple[int, int]
    test_last_set: bool
    rest_s: int
    cue: str


@dataclass(frozen=True)
class CircuitPlan:
    level: int
    work_s: int
    rest_s: int
    rounds: int
    moves: tuple[str, ...]

    @property
    def seconds(self) -> int:
        return self.rounds * len(self.moves) * (self.work_s + self.rest_s)


@dataclass(frozen=True)
class Session:
    template: str
    title: str
    goal: Goal
    pairs: tuple[tuple[PlannedExercise, ...], ...]  # one or two exercises each
    circuit: CircuitPlan | None
    warmup_s: int
    minutes: int  # estimated length
    light: bool
    note: str

    @property
    def exercises(self) -> tuple[PlannedExercise, ...]:
        return tuple(ex for pair in self.pairs for ex in pair)

    @property
    def total_sets(self) -> int:
        return sum(ex.sets for ex in self.exercises)


@dataclass(frozen=True)
class SessionInput:
    goal: Goal
    slot: WeekSlot
    minutes: int
    states: dict[str, ExerciseState]  # by ladder key; missing ladders start at level 1
    available: frozenset[Need] = EVERYDAY
    volume_step: int = 0
    readiness: float | None = None
    circuit_level: int = 1
    high_impact: bool = False
    seed: str = ""  # varies the circuit moves from session to session
    paused: frozenset[str] = frozenset()  # ladders stopped for pain until the user says they're fine


def sets_for(main: bool, step: int) -> int:
    """Sets per exercise: 3 for main movements and 2 for extras at step 0."""
    if main:
        return max(2, min(4, 3 + step))
    # Extras grow only at the top step, and shrink first.
    change = step - 1 if step > 1 else min(step, 0)
    return max(1, min(3, 2 + change))


def build_session(inp: SessionInput) -> Session:
    if inp.minutes not in SESSION_LENGTHS:
        raise ValueError(f"minutes must be one of {SESSION_LENGTHS}, got {inp.minutes}")
    if not MIN_STEP <= inp.volume_step <= MAX_STEP:
        raise ValueError(f"volume_step must be {MIN_STEP}..{MAX_STEP}, got {inp.volume_step}")
    title = TEMPLATE_TITLES[inp.slot.template]
    if inp.slot.template == CIRCUIT:
        circuit = _circuit(inp, inp.minutes * 60 - WARMUP_S, max_rounds=None)
        total = WARMUP_S + circuit.seconds
        note = (
            f"{len(circuit.moves)} moves, {circuit.work_s} s on and {circuit.rest_s} s off, "
            f"{circuit.rounds} rounds. Work hard enough that you can only say a few words."
        )
        return Session(CIRCUIT, title, inp.goal, (), circuit, WARMUP_S, _minutes(total), False, note)

    light = inp.readiness is not None and inp.readiness < LIGHT_BELOW
    step = inp.volume_step
    if inp.readiness is not None and inp.readiness < FEWER_EXTRAS_BELOW:
        step = max(MIN_STEP, step - 1)

    budget = inp.minutes * 60 - WARMUP_S
    finisher = None
    if inp.slot.finisher and not light and inp.minutes >= FINISHER_FROM_MINUTES:
        finisher = _circuit(inp, budget, max_rounds=2)
        budget -= finisher.seconds

    pairs = _fit_pairs(inp, step, light, budget)
    used = sum(_pair_seconds(pair) for pair in pairs)
    total = WARMUP_S + used + (finisher.seconds if finisher else 0)
    session_sets = sum(ex.sets for pair in pairs for ex in pair)
    note = f"{len(pairs)} {'pair' if len(pairs) == 1 else 'pairs'}, {session_sets} sets. Rest {PAIR_REST_S} s between sets in a pair."
    if light:
        note = "A light session after a rough check-in: main movements only, 2 sets each, no test sets. " + note
    elif step < inp.volume_step:
        note = "One set fewer on the extras after a below-average check-in. " + note
    return Session(
        inp.slot.template, title, inp.goal, tuple(pairs), finisher, WARMUP_S, _minutes(total), light, note
    )


def _fit_pairs(inp: SessionInput, step: int, light: bool, budget: int) -> list[tuple[PlannedExercise, ...]]:
    """Every pair that fits gets in at its minimum sets first; extra sets come after.

    So more volume never pushes a whole muscle out of a short session.
    """
    chosen: list[list[PlannedExercise]] = []
    targets: list[list[int]] = []
    used = 0
    for keys in TEMPLATES[inp.slot.template]:
        keys = tuple(
            k
            for k in keys
            if k not in inp.paused and ladder(k).usable_levels(inp.available) and (not light or k in MAIN_LADDERS)
        )
        if not keys:
            continue
        rest = PAIR_REST_S if len(keys) == 2 else SINGLE_REST_S
        pair = [_planned(k, 2 if k in MAIN_LADDERS else 1, rest, inp, light) for k in keys]
        cost = _pair_seconds(pair)
        if chosen and used + cost > budget:
            break
        chosen.append(pair)
        targets.append([2 if light else sets_for(ex.ladder in MAIN_LADDERS, step) for ex in pair])
        used += cost

    order = [(i, j) for i, pair in enumerate(chosen) for j, ex in enumerate(pair) if ex.ladder in MAIN_LADDERS]
    order += [(i, j) for i, pair in enumerate(chosen) for j, ex in enumerate(pair) if ex.ladder not in MAIN_LADDERS]
    grew = True
    while grew:
        grew = False
        for i, j in order:
            ex = chosen[i][j]
            if ex.sets >= targets[i][j]:
                continue
            extra = ladder(ex.ladder).set_seconds(ex.level, ex.target) + ex.rest_s
            if used + extra <= budget:
                chosen[i][j] = replace(ex, sets=ex.sets + 1)
                used += extra
                grew = True
    return [tuple(pair) for pair in chosen]


def _planned(key: str, sets: int, rest: int, inp: SessionInput, light: bool) -> PlannedExercise:
    lad = ladder(key)
    state = inp.states.get(key) or starting_state(key, 1, inp.available)
    level = nearest_usable(lad, state.level, inp.available)
    lo, hi = lad.range_for(level)
    target = max(lo, min(hi, state.target)) if level == state.level else lo
    ex = lad.at(level)
    return PlannedExercise(
        ladder=key,
        key=ex.key,
        name=ex.name,
        level=level,
        sets=sets,
        target=target,
        unit=lad.unit,
        each_side=ex.each_side,
        rep_range=(lo, hi),
        test_last_set=ex.test_last_set and not light,
        rest_s=rest,
        cue=ex.cue,
    )


def _pair_seconds(pair) -> int:
    return sum(ex.sets * (ladder(ex.ladder).set_seconds(ex.level, ex.target) + ex.rest_s) for ex in pair)


def _circuit(inp: SessionInput, budget_s: int, max_rounds: int | None) -> CircuitPlan:
    lvl = CIRCUIT_LEVELS[max(1, min(len(CIRCUIT_LEVELS), inp.circuit_level)) - 1]
    per_round = lvl.moves * (lvl.work_s + lvl.rest_s)
    rounds = min(lvl.rounds, max_rounds or lvl.rounds, max(2, budget_s // per_round))
    offset = int(hashlib.sha256(inp.seed.encode()).hexdigest(), 16) % len(CARDIO_MOVES)
    picked = [CARDIO_MOVES[(offset + i) % len(CARDIO_MOVES)] for i in range(lvl.moves)]
    names = tuple(m.high_impact if inp.high_impact else m.low_impact for m in picked)
    return CircuitPlan(lvl.level, lvl.work_s, lvl.rest_s, rounds, names)


def _minutes(seconds: int) -> int:
    return math.ceil(seconds / 60)


def weekly_sets(sessions: list[Session]) -> dict[Muscle, float]:
    """Sets per muscle, counting indirect work as half a set (Pelland et al. 2026)."""
    totals = {m: 0.0 for m in Muscle}
    for session in sessions:
        for ex in session.exercises:
            for muscle, weight in ladder(ex.ladder).muscles.items():
                totals[muscle] += ex.sets * weight
    return totals


# Where each ladder starts, by training experience. The first session's test sets
# correct a wrong guess within a session or two.
STARTING_LEVELS: dict[Experience, dict[str, int]] = {
    Experience.BEGINNER: {
        "push": 3, "pike": 1, "row": 2, "squat": 2, "lunge": 1, "hinge": 1,
        "curl": 1, "calves": 1, "triceps": 1, "plank": 2, "crunch": 1, "side_plank": 1,
    },
    Experience.INTERMEDIATE: {
        "push": 4, "pike": 2, "row": 3, "squat": 3, "lunge": 1, "hinge": 2,
        "curl": 1, "calves": 2, "triceps": 2, "plank": 2, "crunch": 2, "side_plank": 2,
    },
    Experience.EXPERIENCED: {
        "push": 4, "pike": 2, "row": 3, "squat": 4, "lunge": 2, "hinge": 3,
        "curl": 2, "calves": 2, "triceps": 3, "plank": 3, "crunch": 3, "side_plank": 2,
    },
}


def initial_states(
    experience: Experience,
    available: frozenset[Need],
    push_max: int | None = None,
    push_level: int | None = None,
) -> dict[str, ExerciseState]:
    """Starting levels for every ladder. A push-up max test, if there is one, places
    the push-up ladder exactly."""
    states = {}
    for key, level in STARTING_LEVELS[experience].items():
        if key == "push" and push_max is not None:
            states[key] = starting_state(key, push_level or level, available, max_reps=push_max)
        else:
            states[key] = starting_state(key, level, available)
    assert set(states) == set(LADDERS)
    return states


def rotation(goal: Goal, days: int, sessions_done: int) -> WeekSlot:
    """The next workout: templates repeat in order, so a missed day never skips one."""
    slots = week_plan(goal, days)
    return slots[sessions_done % len(slots)]


def session_to_dict(session: Session) -> dict:
    out = asdict(session)
    out["total_sets"] = session.total_sets
    return out
