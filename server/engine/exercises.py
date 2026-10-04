"""Bodyweight exercise library for session mode.

Each movement is a ladder of levels, easiest first. A person trains one level of each
ladder, adds reps until the top of its range, then moves up a level (double
progression; see docs/training-research.md). The push ladder's first five levels are
the same as engine/levels.py, so a push-up max from the spread-out mode carries over.

Muscle weights follow Pelland et al. 2026: 1 for the muscle a ladder trains directly,
0.5 for muscles it trains indirectly.
"""

from dataclasses import dataclass
from enum import StrEnum

from .common import round_half_up


class Muscle(StrEnum):
    CHEST = "chest"
    BACK = "back"
    SHOULDERS = "shoulders"
    TRICEPS = "triceps"
    BICEPS = "biceps"
    QUADS = "quads"
    GLUTES = "glutes"
    HAMSTRINGS = "hamstrings"
    CALVES = "calves"
    CORE = "core"


# Weekly set targets apply to these; arms, calves and core get what the plan gives them.
MAJOR_MUSCLES = (Muscle.CHEST, Muscle.BACK, Muscle.SHOULDERS, Muscle.QUADS, Muscle.GLUTES, Muscle.HAMSTRINGS)


class Unit(StrEnum):
    REPS = "reps"
    SECONDS = "seconds"


class Need(StrEnum):
    """Household things an exercise needs. Everything else is just floor space."""

    WALL = "wall"
    CHAIR = "chair"  # a sturdy chair, sofa or bed edge to put hands or feet on
    TABLE = "table"  # a sturdy table to lie under for rows: not glass, not folding
    DOORWAY = "doorway"
    STEP = "step"  # a stair or sturdy step
    SMOOTH_FLOOR = "smooth_floor"  # a towel or socks that slide on the floor
    SOFA = "sofa"  # heavy enough to hook the feet under


EVERYDAY = frozenset({Need.WALL, Need.CHAIR, Need.DOORWAY, Need.SMOOTH_FLOOR})


@dataclass(frozen=True)
class Exercise:
    key: str
    name: str
    level: int  # 1 = easiest in its ladder
    cue: str
    each_side: bool = False
    needs: tuple[Need, ...] = ()
    rep_range: tuple[int, int] | None = None  # overrides the ladder's range
    test_last_set: bool = True  # False where going to the limit isn't safe (e.g. Nordic curls)


@dataclass(frozen=True)
class Ladder:
    key: str
    title: str
    unit: Unit
    rep_range: tuple[int, int]
    muscles: dict[Muscle, float]
    exercises: tuple[Exercise, ...]
    seconds_per_rep: float = 3.0  # about 1 s up and 2 s down, for time estimates
    step: int = 1  # how much the target grows per step: 1 rep, or 5 seconds for holds

    def at(self, level: int) -> Exercise:
        if not 1 <= level <= len(self.exercises):
            raise ValueError(f"{self.key} has levels 1-{len(self.exercises)}, got {level}")
        return self.exercises[level - 1]

    def range_for(self, level: int) -> tuple[int, int]:
        return self.at(level).rep_range or self.rep_range

    def usable(self, level: int, available: frozenset[Need]) -> bool:
        return all(need in available for need in self.at(level).needs)

    def usable_levels(self, available: frozenset[Need]) -> list[int]:
        return [ex.level for ex in self.exercises if self.usable(ex.level, available)]

    def set_seconds(self, level: int, target: int) -> int:
        """Rough time for one set, including getting into position."""
        work = target if self.unit == Unit.SECONDS else target * self.seconds_per_rep
        if self.at(level).each_side:
            work *= 2
        return round_half_up(work + 10)


def _ex(key: str, name: str, cue: str, **kw) -> tuple[str, str, str, dict]:
    return key, name, cue, kw


def _ladder(key, title, unit, rep_range, muscles, steps, **kw) -> Ladder:
    exercises = tuple(
        Exercise(key=k, name=n, level=i + 1, cue=c, **extra) for i, (k, n, c, extra) in enumerate(steps)
    )
    return Ladder(key=key, title=title, unit=unit, rep_range=rep_range, muscles=muscles, exercises=exercises, **kw)


LADDERS: dict[str, Ladder] = {
    ladder.key: ladder
    for ladder in (
        _ladder(
            "push",
            "Push-up",
            Unit.REPS,
            (6, 15),
            {Muscle.CHEST: 1, Muscle.TRICEPS: 0.5, Muscle.SHOULDERS: 0.5},
            [
                _ex("pushup_wall", "Wall push-up", "Hands on the wall at shoulder height, body straight, chest to the wall.", needs=(Need.WALL,)),
                _ex("pushup_incline", "Incline push-up", "Hands on a sturdy table or bench, body straight, chest to the edge.", needs=(Need.CHAIR,)),
                _ex("pushup_knee", "Knee push-up", "Body straight from knees to head; lower until your chest nearly touches."),
                _ex("pushup_full", "Push-up", "Hands under shoulders, body straight; lower for 2-3 seconds, chest to the floor."),
                _ex("pushup_decline", "Decline push-up", "Feet on a chair, hands on the floor; lower your chest all the way.", needs=(Need.CHAIR,)),
                _ex("pushup_archer", "Archer push-up", "Hands wide; lower towards one hand while the other arm stays straight.", each_side=True),
                _ex("pushup_pseudo_planche", "Pseudo planche push-up", "Hands by your hips, fingers turned out, lean forward over them.", rep_range=(5, 12)),
            ],
        ),
        _ladder(
            "pike",
            "Pike push-up",
            Unit.REPS,
            (6, 15),
            {Muscle.SHOULDERS: 1, Muscle.TRICEPS: 0.5},
            [
                _ex("pike_hands_up", "Hands-raised pike push-up", "Hands on a chair seat, hips high; lower the top of your head towards the seat.", needs=(Need.CHAIR,)),
                _ex("pike_floor", "Pike push-up", "Hips high in an upside-down V; lower your head towards the floor in front of your hands."),
                _ex("pike_feet_up", "Feet-raised pike push-up", "Feet on a chair, hips over your hands; lower your head towards the floor.", needs=(Need.CHAIR,)),
                _ex("hspu_negative", "Wall handstand push-up, lowering only", "Kick up to a handstand against the wall and lower slowly to your head; come down to reset.", needs=(Need.WALL,), rep_range=(3, 8), test_last_set=False),
            ],
        ),
        _ladder(
            "row",
            "Row",
            Unit.REPS,
            (6, 15),
            {Muscle.BACK: 1, Muscle.BICEPS: 0.5},
            [
                _ex("row_doorway", "Doorway row", "Hold both sides of a door frame, lean back with straight arms, pull your chest to the frame.", needs=(Need.DOORWAY,)),
                _ex("row_table_bent", "Table row, knees bent", "Lie under a sturdy table, grip the edge, feet flat, pull your chest to the edge.", needs=(Need.TABLE,)),
                _ex("row_table", "Table row", "As above with legs straight and body in one line from heels to head.", needs=(Need.TABLE,)),
                _ex("row_table_feet_up", "Table row, feet raised", "Heels on a chair so your body is level; pull your chest to the edge.", needs=(Need.TABLE, Need.CHAIR)),
            ],
        ),
        _ladder(
            "squat",
            "Squat",
            Unit.REPS,
            (6, 15),
            {Muscle.QUADS: 1, Muscle.GLUTES: 0.5},
            [
                _ex("squat_chair", "Chair squat", "Sit back to a chair and stand up without using your hands.", needs=(Need.CHAIR,)),
                _ex("squat_bodyweight", "Squat", "Feet shoulder-width, sit down between your heels as deep as you can, chest up."),
                _ex("split_squat", "Split squat", "Long stride, lower the back knee towards the floor, front heel down.", each_side=True),
                _ex("bulgarian_split_squat", "Bulgarian split squat", "Back foot on a chair; lower until the back knee nearly touches the floor.", each_side=True, needs=(Need.CHAIR,)),
                _ex("shrimp_squat_assisted", "Assisted shrimp squat", "Stand on one leg, hold the other foot behind you, lower the back knee to the floor; a hand on the wall.", each_side=True, needs=(Need.WALL,)),
                _ex("pistol_box", "Box pistol squat", "On one leg, sit down to a chair with the other leg straight out, stand back up.", each_side=True, needs=(Need.CHAIR,), rep_range=(5, 12)),
            ],
        ),
        _ladder(
            "lunge",
            "Lunge",
            Unit.REPS,
            (6, 15),
            {Muscle.QUADS: 1, Muscle.GLUTES: 0.5},
            [
                _ex("reverse_lunge", "Reverse lunge", "Step back and lower the back knee towards the floor; push up through the front heel.", each_side=True),
                _ex("step_up", "Step-up", "Whole foot on a stair or sturdy step; stand up on it without pushing off the back foot, lower slowly.", each_side=True, needs=(Need.STEP,)),
                _ex("deficit_reverse_lunge", "Deficit reverse lunge", "Stand on a step and lunge back down to the floor, so the front leg bends deeper.", each_side=True, needs=(Need.STEP,)),
            ],
        ),
        _ladder(
            "hinge",
            "Hip thrust",
            Unit.REPS,
            (8, 20),
            {Muscle.GLUTES: 1, Muscle.HAMSTRINGS: 0.5},
            [
                _ex("glute_bridge", "Glute bridge", "On your back, feet flat, push through the heels and lift your hips; squeeze for a second."),
                _ex("glute_bridge_single", "Single-leg glute bridge", "As above on one leg, the other knee pulled in.", each_side=True),
                _ex("hip_thrust", "Hip thrust", "Shoulders on a sofa or bed edge, feet flat; lower your hips and drive them up.", needs=(Need.CHAIR,)),
                _ex("hip_thrust_single", "Single-leg hip thrust", "As above on one leg.", each_side=True, needs=(Need.CHAIR,)),
            ],
        ),
        _ladder(
            "curl",
            "Leg curl",
            Unit.REPS,
            (6, 15),
            {Muscle.HAMSTRINGS: 1, Muscle.GLUTES: 0.5},
            [
                _ex("leg_curl_slide", "Sliding leg curl", "On your back, heels on a towel, hips up; slide the heels in and back out slowly.", needs=(Need.SMOOTH_FLOOR,)),
                _ex("leg_curl_slide_single", "Single-leg sliding leg curl", "As above with one heel on the towel.", each_side=True, needs=(Need.SMOOTH_FLOOR,)),
                _ex("nordic_negative", "Nordic curl, lowering only", "Kneel with feet hooked under a heavy sofa; lower your body forward as slowly as you can, catch with your hands.", needs=(Need.SOFA,), rep_range=(3, 8), test_last_set=False),
            ],
        ),
        _ladder(
            "calves",
            "Calf raise",
            Unit.REPS,
            (10, 20),
            {Muscle.CALVES: 1},
            [
                _ex("calf_raise", "Calf raise", "Rise onto your toes, pause, lower slowly; a hand on the wall for balance.", needs=(Need.WALL,)),
                _ex("calf_raise_single", "Single-leg calf raise", "As above on one foot.", each_side=True, needs=(Need.WALL,)),
                _ex("calf_raise_step", "Single-leg calf raise on a step", "Ball of the foot on a step; drop the heel below the step, then rise all the way.", each_side=True, needs=(Need.STEP,)),
            ],
            seconds_per_rep=2.5,
        ),
        _ladder(
            "triceps",
            "Close push-up",
            Unit.REPS,
            (6, 15),
            {Muscle.TRICEPS: 1, Muscle.CHEST: 0.5},
            [
                _ex("close_pushup_incline", "Close incline push-up", "Hands close together on a table edge, elbows tucked to your sides.", needs=(Need.CHAIR,)),
                _ex("close_pushup_knee", "Close knee push-up", "On your knees, hands under your chest, elbows brushing your ribs."),
                _ex("diamond_pushup", "Diamond push-up", "Thumbs and index fingers touching under your chest; elbows back, not out."),
                _ex("triceps_extension", "Bodyweight triceps extension", "Forearms on a chair seat, body straight; lower your head below the seat by bending only the elbows, then press back.", needs=(Need.CHAIR,)),
            ],
        ),
        _ladder(
            "plank",
            "Plank",
            Unit.SECONDS,
            (20, 60),
            {Muscle.CORE: 1},
            [
                _ex("plank_knee", "Knee plank", "On elbows and knees, body straight, belly tight."),
                _ex("plank", "Plank", "On elbows and toes, squeeze your glutes, don't let the hips sag."),
                _ex("plank_long", "Long plank", "Elbows a hand's width in front of your shoulders; much harder."),
                _ex("body_saw", "Body saw", "Plank with feet on a towel; slide your body back and forth a few centimetres.", needs=(Need.SMOOTH_FLOOR,)),
            ],
            step=5,
        ),
        _ladder(
            "crunch",
            "Core curl",
            Unit.REPS,
            (8, 20),
            {Muscle.CORE: 1},
            [
                _ex("dead_bug", "Dead bug", "On your back, arms and knees up; lower the opposite arm and leg, low back pressed down.", each_side=True),
                _ex("reverse_crunch", "Reverse crunch", "On your back, knees bent; curl your hips off the floor towards your chest, lower slowly."),
                _ex("leg_raise", "Lying leg raise", "Legs straight, low back pressed down; lower the legs slowly, lift them back up."),
                _ex("hollow_rock", "Hollow rock", "Hold a banana shape on your back and rock from shoulders to hips."),
            ],
        ),
        _ladder(
            "side_plank",
            "Side plank",
            Unit.SECONDS,
            (15, 45),
            {Muscle.CORE: 1},
            [
                _ex("side_plank_knee", "Knee side plank", "On one elbow and the side of your knee, hips lifted in line.", each_side=True),
                _ex("side_plank", "Side plank", "On one elbow and the side of your foot, body in one line.", each_side=True),
                _ex("side_plank_leg_up", "Side plank, top leg raised", "As above, lift and hold the top leg.", each_side=True),
            ],
            step=5,
        ),
    )
}


@dataclass(frozen=True)
class CardioMove:
    key: str
    low_impact: str
    high_impact: str
    cue: str


# Interval circuits for the "get fit" goal. Low-impact versions are the default.
CARDIO_MOVES = (
    CardioMove("knees", "March in place", "High knees", "Drive your knees up and swing your arms."),
    CardioMove("jacks", "Step jacks", "Jumping jacks", "Step or jump out wide while your arms go overhead."),
    CardioMove("squat_reach", "Squat to calf raise", "Jump squat", "Sit into a squat, then rise or jump up tall."),
    CardioMove("climbers", "Slow mountain climbers", "Mountain climbers", "In a push-up position, bring one knee at a time to your chest."),
    CardioMove("skaters", "Skater steps", "Skater hops", "Step or hop side to side, landing softly on one leg."),
    CardioMove("burpee", "Step-back burpee", "Burpee", "Hands down, step or jump back to a plank, come back up and stand tall."),
    CardioMove("boxing", "Shadow boxing", "Shadow boxing with a squat", "Quick straight punches with a light bounce."),
    CardioMove("lunge", "Reverse lunge", "Switch lunge", "Step back into a lunge and alternate legs."),
)


@dataclass(frozen=True)
class CircuitLevel:
    level: int
    work_s: int
    rest_s: int
    rounds: int
    moves: int


CIRCUIT_LEVELS = (
    CircuitLevel(1, 20, 40, 3, 4),
    CircuitLevel(2, 30, 30, 3, 4),
    CircuitLevel(3, 30, 30, 4, 4),
    CircuitLevel(4, 40, 20, 4, 4),
    CircuitLevel(5, 40, 20, 4, 5),
)


def ladder(key: str) -> Ladder:
    try:
        return LADDERS[key]
    except KeyError:
        raise ValueError(f"unknown ladder {key!r}") from None


@dataclass(frozen=True)
class ExerciseState:
    """Where someone is on one ladder."""

    ladder: str
    level: int
    target: int  # reps per set, or seconds for holds
    below_range: int = 0  # sessions in a row the last set fell below the range


def starting_state(
    ladder_key: str,
    level: int,
    available: frozenset[Need] = EVERYDAY,
    max_reps: int | None = None,
) -> ExerciseState:
    """A first guess. The first session's last set corrects it quickly.

    With a known max (the push-up max test), sets start at about 70% of it, which
    leaves 2-4 reps in hand on the first sets.
    """
    lad = ladder(ladder_key)
    lvl = nearest_usable(lad, level, available)
    lo, hi = lad.range_for(lvl)
    if max_reps is None:
        return ExerciseState(ladder_key, lvl, lo)
    guess = round_half_up(0.7 * max_reps)
    if guess > hi:
        nxt = next_usable(lad, lvl, available)
        if nxt is not None:
            return ExerciseState(ladder_key, nxt, lad.range_for(nxt)[0])
    return ExerciseState(ladder_key, lvl, max(lo, min(hi, guess)))


def nearest_usable(lad: Ladder, level: int, available: frozenset[Need]) -> int:
    """The level itself if it's usable, else the closest easier one, else the easiest usable."""
    usable = lad.usable_levels(available)
    if not usable:
        raise ValueError(f"no {lad.key} exercise works with what's available")
    easier = [lvl for lvl in usable if lvl <= level]
    return max(easier) if easier else min(usable)


def next_usable(lad: Ladder, level: int, available: frozenset[Need]) -> int | None:
    harder = [lvl for lvl in lad.usable_levels(available) if lvl > level]
    return min(harder) if harder else None


def previous_usable(lad: Ladder, level: int, available: frozenset[Need]) -> int | None:
    easier = [lvl for lvl in lad.usable_levels(available) if lvl < level]
    return max(easier) if easier else None


def describe_target(lad: Ladder, level: int, target: int) -> str:
    """'12 reps', '12 reps each side', '30 s'."""
    if lad.unit == Unit.SECONDS:
        text = f"{target} s"
    else:
        text = f"{target} rep" if target == 1 else f"{target} reps"
    return text + (" each side" if lad.at(level).each_side else "")

