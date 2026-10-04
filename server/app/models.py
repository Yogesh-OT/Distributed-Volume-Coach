"""Database tables. One PostgreSQL database in production, SQLite in tests."""

import datetime as dt
import uuid

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _user_fk() -> Mapped[str]:
    return mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    auth_uid: Mapped[str] = mapped_column(String(128), unique=True)
    timezone: Mapped[str] = mapped_column(String(64))
    birth_year: Mapped[int] = mapped_column(Integer)  # year only: enough for the 18+ check
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Consent(Base):
    __tablename__ = "consents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = _user_fk()
    kind: Mapped[str] = mapped_column(String(32))  # terms, photos, health_connect, photo_backup
    granted_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    revoked_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))


class Profile(Base):
    """Questionnaire answers. Every edit adds a new version; plans record which one they used."""

    __tablename__ = "profiles"
    __table_args__ = (UniqueConstraint("user_id", "version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = _user_fk()
    version: Mapped[int] = mapped_column(Integer)
    goal: Mapped[str] = mapped_column(String(32))
    training_months: Mapped[int] = mapped_column(Integer)
    sex: Mapped[str | None] = mapped_column(String(8))
    wake_time: Mapped[str] = mapped_column(String(5))
    window_start: Mapped[str] = mapped_column(String(5))
    window_end: Mapped[str] = mapped_column(String(5))
    quiet_start: Mapped[str] = mapped_column(String(5))
    quiet_end: Mapped[str] = mapped_column(String(5))
    prompt_limit: Mapped[int] = mapped_column(Integer)
    screening_flags: Mapped[list] = mapped_column(JSON, default=list)
    clearance_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class MaxTest(Base):
    __tablename__ = "max_tests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = _user_fk()
    exercise: Mapped[str] = mapped_column(String(32))
    reps: Mapped[int] = mapped_column(Integer)
    level: Mapped[int] = mapped_column(Integer, default=4, server_default="4")  # engine/levels.py
    tested_on: Mapped[dt.date] = mapped_column(Date)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class BodyMeasurement(Base):
    __tablename__ = "body_measurements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = _user_fk()
    measured_on: Mapped[dt.date] = mapped_column(Date)
    height_cm: Mapped[float | None] = mapped_column(Float)
    weight_kg: Mapped[float | None] = mapped_column(Float)
    arm_span_cm: Mapped[float | None] = mapped_column(Float)
    waist_cm: Mapped[float | None] = mapped_column(Float)
    wrist_cm: Mapped[float | None] = mapped_column(Float)
    resting_hr: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(16))  # tape, scale, health_connect, photo
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Checkin(Base):
    __tablename__ = "checkins"
    __table_args__ = (UniqueConstraint("user_id", "date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = _user_fk()
    date: Mapped[dt.date] = mapped_column(Date)
    local_time: Mapped[str] = mapped_column(String(5))
    sleep_quality: Mapped[int] = mapped_column(Integer)
    soreness: Mapped[int] = mapped_column(Integer)
    energy: Mapped[int] = mapped_column(Integer)
    sleep_minutes: Mapped[int | None] = mapped_column(Integer)  # only when Health Connect is linked
    source: Mapped[str] = mapped_column(String(16), default="manual")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Plan(Base):
    __tablename__ = "plans"
    __table_args__ = (UniqueConstraint("user_id", "date", "exercise"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = _user_fk()
    date: Mapped[dt.date] = mapped_column(Date)
    exercise: Mapped[str] = mapped_column(String(32))
    kind: Mapped[str] = mapped_column(String(16))
    sets: Mapped[list] = mapped_column(JSON)
    policy: Mapped[dict] = mapped_column(JSON)
    reason: Mapped[str] = mapped_column(Text)
    readiness: Mapped[float] = mapped_column(Float)
    max_reps: Mapped[int] = mapped_column(Integer)
    level: Mapped[int | None] = mapped_column(Integer)
    load: Mapped[float] = mapped_column(Float)
    engine_version: Mapped[str] = mapped_column(String(16))
    profile_version: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(16))  # server or fallback
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class SetLog(Base):
    __tablename__ = "set_logs"
    __table_args__ = (Index("ix_set_logs_user_date", "user_id", "date"),)  # progress queries

    # Made on the phone, so a retried upload can never count a set twice.
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = _user_fk()
    date: Mapped[dt.date] = mapped_column(Date)
    exercise: Mapped[str] = mapped_column(String(32))
    set_ref: Mapped[str] = mapped_column(String(8))
    target_reps: Mapped[int] = mapped_column(Integer)
    done_reps: Mapped[int] = mapped_column(Integer)
    rating: Mapped[str] = mapped_column(String(8))  # easy, solid, hard, pain, skipped
    logged_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    local_time: Mapped[str] = mapped_column(String(5))
    received_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)



class Progression(Base):
    """One row per user, exercise and week: the outcome of that week's review. See engine/progression.py."""

    __tablename__ = "progressions"
    __table_args__ = (UniqueConstraint("user_id", "exercise", "week_start"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = _user_fk()
    exercise: Mapped[str] = mapped_column(String(32))
    week_start: Mapped[dt.date] = mapped_column(Date)  # a Monday
    extra_sets: Mapped[int] = mapped_column(Integer, default=0)
    extra_reps: Mapped[int] = mapped_column(Integer, default=0)
    last_step: Mapped[str | None] = mapped_column(String(8))  # sets or reps
    decision: Mapped[str] = mapped_column(String(24))
    note: Mapped[str] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)



# --- Session mode (engine/sessions.py) ---


class SessionSettings(Base):
    __tablename__ = "session_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    mode: Mapped[str] = mapped_column(String(16))  # sessions or spread
    goal: Mapped[str] = mapped_column(String(16))  # muscle or fit
    days_per_week: Mapped[int] = mapped_column(Integer)
    session_minutes: Mapped[int] = mapped_column(Integer)
    weekdays: Mapped[list] = mapped_column(JSON, default=list)  # 0 = Monday
    available: Mapped[list] = mapped_column(JSON, default=list)  # engine.exercises.Need values
    high_impact: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ExerciseStateRow(Base):
    """Where the user is on each ladder. The row with ladder "circuit" holds the circuit level."""

    __tablename__ = "exercise_states"
    __table_args__ = (UniqueConstraint("user_id", "ladder"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = _user_fk()
    ladder: Mapped[str] = mapped_column(String(16))
    level: Mapped[int] = mapped_column(Integer)
    target: Mapped[int] = mapped_column(Integer)
    below_range: Mapped[int] = mapped_column(Integer, default=0)
    paused: Mapped[bool] = mapped_column(Boolean, default=False)  # stopped for pain
    last_rating: Mapped[str | None] = mapped_column(String(16))  # circuits only
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class SessionPlan(Base):
    __tablename__ = "session_plans"
    __table_args__ = (UniqueConstraint("user_id", "date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = _user_fk()
    date: Mapped[dt.date] = mapped_column(Date)
    template: Mapped[str] = mapped_column(String(16))
    goal: Mapped[str] = mapped_column(String(16))
    minutes: Mapped[int] = mapped_column(Integer)  # estimated length
    volume_step: Mapped[int] = mapped_column(Integer)
    sleep_quality: Mapped[int | None] = mapped_column(Integer)
    soreness: Mapped[int | None] = mapped_column(Integer)
    energy: Mapped[int | None] = mapped_column(Integer)
    readiness: Mapped[float | None] = mapped_column(Float)
    payload: Mapped[dict] = mapped_column(JSON)  # engine.sessions.session_to_dict
    engine_version: Mapped[str] = mapped_column(String(16))
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    finished: Mapped[bool | None] = mapped_column(Boolean)
    quit_reason: Mapped[str | None] = mapped_column(String(16))
    summary: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class SessionSetLog(Base):
    __tablename__ = "session_set_logs"
    __table_args__ = (Index("ix_session_set_logs_user_date", "user_id", "date"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # made on the phone
    user_id: Mapped[str] = _user_fk()
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("session_plans.id", ondelete="CASCADE"), index=True)
    date: Mapped[dt.date] = mapped_column(Date)
    ladder: Mapped[str] = mapped_column(String(16))
    exercise_key: Mapped[str] = mapped_column(String(32))
    level: Mapped[int] = mapped_column(Integer)
    set_number: Mapped[int] = mapped_column(Integer)
    target: Mapped[int] = mapped_column(Integer)
    done: Mapped[int] = mapped_column(Integer)  # reps, or seconds for holds
    effort: Mapped[str] = mapped_column(String(8))  # easy, good, hard, max
    tested: Mapped[bool] = mapped_column(Boolean, default=False)  # the last set, as far as form allows
    pain: Mapped[bool] = mapped_column(Boolean, default=False)
    logged_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class SessionReview(Base):
    """The weekly volume review's outcome. See engine/session_progression.py."""

    __tablename__ = "session_reviews"
    __table_args__ = (UniqueConstraint("user_id", "week_start"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = _user_fk()
    week_start: Mapped[dt.date] = mapped_column(Date)
    volume_step: Mapped[int] = mapped_column(Integer)
    decision: Mapped[str] = mapped_column(String(24))
    note: Mapped[str] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


# Tables that hold per-user rows, in a safe deletion order (users last).
USER_TABLES = (
    SessionSetLog,
    SessionPlan,
    SessionReview,
    ExerciseStateRow,
    SessionSettings,
    SetLog,
    Plan,
    Checkin,
    Progression,
    BodyMeasurement,
    MaxTest,
    Profile,
    Consent,
)
