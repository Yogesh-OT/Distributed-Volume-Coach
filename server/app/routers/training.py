import datetime as dt

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from engine import progress as progress_engine
from engine.plan import PlanKind
from engine.planner import PlannerInput, build_plan
from engine.readiness import readiness
from engine.safety import max_test_eligibility

from ..auth import current_user
from ..db import get_db
from ..errors import api_error
from ..models import BodyMeasurement, Checkin, MaxTest, Plan, SetLog, User
from ..schemas import (
    CheckinIn,
    DayOut,
    FallbackPlanIn,
    MaxTestIn,
    MaxTestOut,
    PlanOut,
    ProgressOut,
    SetLogBatchIn,
    SetLogBatchOut,
    WeightOut,
)
from ..timeutil import require_near_today, user_today
from .profile import latest_profile

router = APIRouter(prefix="/v1", tags=["training"])


def _latest_max_test(db: Session, user: User, exercise: str) -> MaxTest | None:
    return db.scalar(
        select(MaxTest)
        .where(MaxTest.user_id == user.id, MaxTest.exercise == exercise)
        .order_by(MaxTest.tested_on.desc(), MaxTest.id.desc())
        .limit(1)
    )


def _find_plan(db: Session, user: User, day: dt.date, exercise: str) -> Plan | None:
    return db.scalar(select(Plan).where(Plan.user_id == user.id, Plan.date == day, Plan.exercise == exercise))


@router.post("/max-tests", status_code=201, response_model=MaxTestOut)
def record_max_test(
    body: MaxTestIn, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    require_near_today(request, user, body.tested_on)
    profile = latest_profile(db, user)
    last = _latest_max_test(db, user, body.exercise)
    eligibility = max_test_eligibility(
        profile.screening_flags, profile.clearance_confirmed, last.tested_on if last else None, body.tested_on
    )
    if not eligibility.allowed:
        extra = {"next_allowed": eligibility.next_allowed.isoformat()} if eligibility.next_allowed else {}
        raise api_error(409, eligibility.code, eligibility.message, **extra)

    test = MaxTest(user_id=user.id, exercise=body.exercise, reps=body.reps, tested_on=body.tested_on)
    db.add(test)
    db.commit()
    return test


@router.post("/checkins", response_model=PlanOut)
def check_in(
    body: CheckinIn,
    request: Request,
    response: Response,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Saves the morning check-in and returns today's plan, built now from last night's sleep."""
    require_near_today(request, user, body.date)

    existing = _find_plan(db, user, body.date, body.exercise)
    if existing is not None:
        return existing  # one plan per day: a repeated check-in gets the same plan back

    max_test = _latest_max_test(db, user, body.exercise)
    if max_test is None:
        raise api_error(409, "max_test_required", "Do a max test first so the plan can be sized for you.")
    profile = latest_profile(db, user)

    plan = build_plan(
        PlannerInput(
            date=body.date.isoformat(),
            exercise=body.exercise,
            checkin_time=body.local_time,
            window_start=profile.window_start,
            window_end=profile.window_end,
            quiet_hours=(profile.quiet_start, profile.quiet_end),
            prompt_limit=profile.prompt_limit,
            training_months=profile.training_months,
            max_reps=max_test.reps,
            sleep_quality=body.sleep_quality,
            soreness=body.soreness,
            energy=body.energy,
            seed=f"{user.id}:{body.date.isoformat()}",
        )
    )

    _save_checkin(db, user, body)
    row = Plan(
        user_id=user.id,
        date=body.date,
        exercise=plan.exercise,
        kind=str(plan.kind),
        sets=[{"ref": s.ref, "at": s.at, "target_reps": s.target_reps} for s in plan.sets],
        policy=plan.policy.to_dict(),
        reason=plan.reason,
        readiness=plan.readiness,
        max_reps=plan.max_reps,
        load=plan.load,
        engine_version=plan.engine_version,
        profile_version=profile.version,
        source="server",
    )
    db.add(row)
    db.commit()
    response.status_code = 201
    return row


def _save_checkin(db: Session, user: User, body: CheckinIn) -> None:
    exists = db.scalar(select(Checkin.id).where(Checkin.user_id == user.id, Checkin.date == body.date))
    if exists is None:
        db.add(
            Checkin(
                user_id=user.id,
                date=body.date,
                local_time=body.local_time,
                sleep_quality=body.sleep_quality,
                soreness=body.soreness,
                energy=body.energy,
                sleep_minutes=body.sleep_minutes,
            )
        )


@router.get("/plans/{day}", response_model=PlanOut)
def get_plan(
    day: dt.date, exercise: str = "pushup", user: User = Depends(current_user), db: Session = Depends(get_db)
):
    plan = _find_plan(db, user, day, exercise)
    if plan is None:
        raise api_error(404, "no_plan", "There's no plan for that day.")
    return plan


@router.post("/plans/fallback", response_model=PlanOut)
def upload_fallback_plan(
    body: FallbackPlanIn, response: Response, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    """Stores a plan the phone built offline. If the server already has a plan for that day, it wins."""
    existing = _find_plan(db, user, body.date, body.exercise)
    if existing is not None:
        return existing

    _save_checkin(db, user, body.checkin)
    row = Plan(
        user_id=user.id,
        date=body.date,
        exercise=body.exercise,
        kind=str(PlanKind.TRAINING),
        sets=[s.model_dump() for s in body.sets],
        policy=body.policy,
        reason=body.reason,
        readiness=round(readiness(body.checkin.sleep_quality, body.checkin.soreness, body.checkin.energy), 2),
        max_reps=body.max_reps,
        load=body.load,
        engine_version=body.engine_version,
        profile_version=None,
        source="fallback",
    )
    db.add(row)
    db.commit()
    response.status_code = 201
    return row


@router.post("/set-logs/batch", response_model=SetLogBatchOut)
def upload_set_logs(body: SetLogBatchIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    unique = {str(log.id): log for log in body.logs}  # repeats inside one batch count once
    already = set(db.scalars(select(SetLog.id).where(SetLog.id.in_(list(unique)))))
    for log_id, log in unique.items():
        if log_id in already:
            continue
        db.add(
            SetLog(
                id=log_id,
                user_id=user.id,
                date=log.date,
                exercise=log.exercise,
                set_ref=log.set_ref,
                target_reps=log.target_reps,
                done_reps=log.done_reps,
                rating=log.rating,
                logged_at=log.logged_at,
                local_time=log.local_time,
            )
        )
    db.commit()
    accepted = len(unique) - len(already)
    return SetLogBatchOut(accepted=accepted, duplicates=len(body.logs) - accepted)


@router.get("/progress", response_model=ProgressOut)
def get_progress(
    request: Request,
    exercise: str = "pushup",
    days: int = Query(default=56, ge=1, le=366),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    since = user_today(request, user) - dt.timedelta(days=days - 1)
    tests = db.scalars(
        select(MaxTest)
        .where(MaxTest.user_id == user.id, MaxTest.exercise == exercise)
        .order_by(MaxTest.tested_on, MaxTest.id)
    ).all()
    logs = db.scalars(
        select(SetLog).where(SetLog.user_id == user.id, SetLog.exercise == exercise, SetLog.date >= since)
    ).all()
    weights = db.scalars(
        select(BodyMeasurement)
        .where(BodyMeasurement.user_id == user.id, BodyMeasurement.weight_kg.is_not(None))
        .order_by(BodyMeasurement.measured_on, BodyMeasurement.id)
    ).all()

    summary = progress_engine.daily_summary(
        [progress_engine.LogRow(log.date, log.done_reps, log.rating) for log in logs]
    )
    return ProgressOut(
        exercise=exercise,
        max_tests=[MaxTestOut.model_validate(t) for t in tests],
        days=[DayOut(date=s.day, sets_done=s.sets_done, reps_done=s.reps_done, hard_sets=s.hard_sets) for s in summary],
        weights=[WeightOut(measured_on=w.measured_on, weight_kg=w.weight_kg) for w in weights],
    )
