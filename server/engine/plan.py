from dataclasses import asdict, dataclass, field
from enum import StrEnum


class PlanKind(StrEnum):
    TRAINING = "training"
    MOBILITY = "mobility"  # readiness too low for training sets
    WINDOW_PASSED = "window_passed"  # checked in after the training window closed


@dataclass(frozen=True)
class PlannedSet:
    ref: str
    at: str  # local HH:MM
    target_reps: int


@dataclass(frozen=True)
class Policy:
    """In-day rules. Sent inside every plan and applied on the phone."""

    window_end: str
    quiet_hours: tuple[str, str]
    scale_remaining_reps: float = 0.8
    delay_remaining_min: int = 30
    end_day_after_hard_sets: int = 2
    min_gap_min: int = 45

    def to_dict(self) -> dict:
        return {
            "on_hard": {
                "scale_remaining_reps": self.scale_remaining_reps,
                "delay_remaining_min": self.delay_remaining_min,
            },
            "end_day_after_hard_sets": self.end_day_after_hard_sets,
            "on_pain": "stop_exercise_today",
            "min_gap_min": self.min_gap_min,
            "window_end": self.window_end,
            "quiet_hours": list(self.quiet_hours),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Policy":
        return cls(
            window_end=d["window_end"],
            quiet_hours=(d["quiet_hours"][0], d["quiet_hours"][1]),
            scale_remaining_reps=d["on_hard"]["scale_remaining_reps"],
            delay_remaining_min=d["on_hard"]["delay_remaining_min"],
            end_day_after_hard_sets=d["end_day_after_hard_sets"],
            min_gap_min=d["min_gap_min"],
        )


@dataclass(frozen=True)
class Plan:
    date: str  # ISO date, user's local calendar
    exercise: str
    kind: PlanKind
    sets: list[PlannedSet]
    policy: Policy
    reason: str
    readiness: float
    max_reps: int
    load: float
    engine_version: str
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "exercise": self.exercise,
            "kind": str(self.kind),
            "sets": [asdict(s) for s in self.sets],
            "policy": self.policy.to_dict(),
            "reason": self.reason,
            "readiness": self.readiness,
            "max_reps": self.max_reps,
            "load": self.load,
            "engine_version": self.engine_version,
        }
