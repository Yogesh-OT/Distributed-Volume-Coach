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


# Tables that hold per-user rows, in a safe deletion order (users last).
USER_TABLES = (SetLog, Plan, Checkin, BodyMeasurement, MaxTest, Profile, Consent)
