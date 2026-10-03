"""Request and response bodies. Validation errors come back as HTTP 422."""

import datetime as dt
import uuid
from typing import Annotated, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

from engine.common import to_minutes
from engine.levels import DEFAULT_LEVEL, LEVELS
from engine.safety import SCREENING_FLAGS

HHMM = Annotated[str, StringConstraints(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")]
Exercise = Literal["pushup"]
Rating = Literal["easy", "solid", "hard", "pain", "skipped"]
ScreeningFlag = Literal[SCREENING_FLAGS]  # type: ignore[valid-type]


def _in_quiet(minute: int, quiet_start: int, quiet_end: int) -> bool:
    if quiet_start == quiet_end:
        return False  # no quiet hours
    if quiet_start < quiet_end:
        return quiet_start <= minute < quiet_end
    return minute >= quiet_start or minute < quiet_end  # wraps past midnight


class ProfileIn(BaseModel):
    goal: Literal["more_pushups", "strength_habit"]
    training_months: int = Field(ge=0, le=600)
    sex: Literal["male", "female"] | None = None
    wake_time: HHMM
    window_start: HHMM
    window_end: HHMM
    quiet_start: HHMM
    quiet_end: HHMM
    prompt_limit: int = Field(ge=1, le=12)
    screening_flags: list[ScreeningFlag] = Field(default_factory=list)
    clearance_confirmed: bool = False

    @model_validator(mode="after")
    def _check_times(self) -> "ProfileIn":
        start, end = to_minutes(self.window_start), to_minutes(self.window_end)
        if end - start < 60:
            raise ValueError("The training window must be at least an hour long and end after it starts.")
        qs, qe = to_minutes(self.quiet_start), to_minutes(self.quiet_end)
        if _in_quiet(start, qs, qe) or _in_quiet(end - 1, qs, qe) or (qs != qe and start <= qs < end):
            raise ValueError("The training window overlaps your quiet hours.")
        self.screening_flags = sorted(set(self.screening_flags))
        return self


class ProfileOut(ProfileIn):
    model_config = ConfigDict(from_attributes=True)

    version: int
    created_at: dt.datetime


class OnboardingIn(BaseModel):
    timezone: str
    birth_year: int = Field(ge=1900, le=2100)
    confirmed_adult: bool
    accepted_terms: bool
    profile: ProfileIn

    @field_validator("timezone")
    @classmethod
    def _known_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"Unknown time zone: {value}") from exc
        return value


class OnboardingOut(BaseModel):
    user_id: str
    profile: ProfileOut


class MaxTestIn(BaseModel):
    exercise: Exercise = "pushup"
    reps: int = Field(ge=1, le=500)
    level: int = Field(default=DEFAULT_LEVEL, ge=1, le=len(LEVELS))
    tested_on: dt.date


class MaxTestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    exercise: str
    reps: int
    level: int
    tested_on: dt.date


class LevelSuggestionOut(BaseModel):
    direction: Literal["up", "down"]
    level: int
    message: str


class MaxTestResultOut(MaxTestOut):
    suggestion: LevelSuggestionOut | None = None


class StreakOut(BaseModel):
    current: int
    best: int
    today_on_plan: bool
    rest_pass_available: bool
    rest_pass_days: list[dt.date]


class BodyMeasurementIn(BaseModel):
    measured_on: dt.date
    height_cm: float | None = Field(default=None, ge=120, le=230)
    weight_kg: float | None = Field(default=None, ge=30, le=250)
    arm_span_cm: float | None = Field(default=None, ge=100, le=250)
    waist_cm: float | None = Field(default=None, ge=40, le=200)
    wrist_cm: float | None = Field(default=None, ge=10, le=30)
    resting_hr: int | None = Field(default=None, ge=30, le=120)
    source: Literal["tape", "scale", "health_connect", "photo"] = "tape"

    @model_validator(mode="after")
    def _not_empty(self) -> "BodyMeasurementIn":
        values = (self.height_cm, self.weight_kg, self.arm_span_cm, self.waist_cm, self.wrist_cm, self.resting_hr)
        if all(v is None for v in values):
            raise ValueError("Send at least one measurement.")
        return self


class ProfileLineOut(BaseModel):
    key: str
    label: str
    headline: str
    detail: str
    value: float | None


class BodyProfileOut(BaseModel):
    measured_on: dt.date
    lines: list[ProfileLineOut]


class CheckinIn(BaseModel):
    date: dt.date
    local_time: HHMM
    sleep_quality: int = Field(ge=1, le=5)
    soreness: int = Field(ge=1, le=5)
    energy: int = Field(ge=1, le=5)
    sleep_minutes: int | None = Field(default=None, ge=0, le=1440)
    exercise: Exercise = "pushup"


class PlannedSetIO(BaseModel):
    ref: Annotated[str, StringConstraints(pattern=r"^s\d{1,2}$")]
    at: HHMM
    target_reps: int = Field(ge=1, le=500)


class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: dt.date
    exercise: str
    kind: str
    sets: list[PlannedSetIO]
    policy: dict
    reason: str
    readiness: float
    max_reps: int
    level: int | None = None
    load: float
    engine_version: str
    source: str


class FallbackPlanIn(BaseModel):
    """A plan the phone made offline, uploaded once a connection returns."""

    date: dt.date
    exercise: Exercise = "pushup"
    sets: list[PlannedSetIO] = Field(max_length=16)
    policy: dict
    reason: str = Field(max_length=500)
    max_reps: int = Field(ge=1, le=500)
    level: int | None = Field(default=None, ge=1, le=len(LEVELS))
    load: float = Field(gt=0, le=1)
    engine_version: str = Field(max_length=16)
    checkin: CheckinIn


class SetLogIn(BaseModel):
    id: uuid.UUID
    date: dt.date
    exercise: Exercise = "pushup"
    set_ref: Annotated[str, StringConstraints(pattern=r"^s\d{1,2}$")]
    target_reps: int = Field(ge=1, le=500)
    done_reps: int = Field(ge=0, le=500)
    rating: Rating
    logged_at: AwareDatetime
    local_time: HHMM


class SetLogBatchIn(BaseModel):
    logs: list[SetLogIn] = Field(min_length=1, max_length=500)


class SetLogBatchOut(BaseModel):
    accepted: int
    duplicates: int


class DayOut(BaseModel):
    date: dt.date
    sets_done: int
    reps_done: int
    hard_sets: int


class WeightOut(BaseModel):
    measured_on: dt.date
    weight_kg: float


class ProgressOut(BaseModel):
    exercise: str
    max_tests: list[MaxTestOut]
    days: list[DayOut]
    weights: list[WeightOut]
    streak: StreakOut
