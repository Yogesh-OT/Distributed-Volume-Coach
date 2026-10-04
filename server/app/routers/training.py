import datetime as dt

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from engine import progress as progress_engine
from engine.common import experience_for, to_minutes
from engine.levels import suggest
from engine.plan import PlanKind
from engine.planner import PlannerInput, base_reps_for, build_plan, set_limits
from engine.progression import Progression as ProgressionState
from engine.progression import WeekStats, review_week, week_start
from engine.readiness import readiness
from engine.safety import max_test_eligibility
from engine.streak import DayRecord, compute_streak

from ..auth import current_user
from ..db import get_db
from ..errors import api_error
from ..models import BodyMeasurement, Checkin, MaxTest, Plan, Profile, Progression, SetLog, User
from ..schemas import (
    CheckinIn,
    DayOut,
    FallbackPlanIn,
    LevelSuggestionOut,
    MaxTestIn,
    MaxTestOut,
    MaxTestResultOut,
    PlanOut,
    ProgressOut,
    SetLogBatchIn,
    SetLogBatchOut,
    StreakOut,
    WeightOut,
)
from ..timeutil import require_near_today, user_today
from .profile import latest_profile

router = APIRouter(prefix="/v1", tags=["training"])


def _latest_max_test(db: Session, user: User, exercise: str, level: int | None = None) -> MaxTest | None:
    query = select(MaxTest).where(MaxTest.user_id == user.id, MaxTest.exercise == exercise)
    if level is not None:
        query = query.where(MaxTest.level == level)
    return db.scalar(query.order_by(MaxTest.tested_on.desc(), MaxTest.id.desc()).limit(1))


def _find_plan(db: Session, user: User, day: dt.date, exercise: str) -> Plan | None:
    return db.scalar(select(Plan).where(Plan.user_id == user.id, Plan.date == day, Plan.exercise == exercise))


@router.post("/max-tests", status_code=201, response_model=MaxTestResultOut)
def record_max_test(
    body: MaxTestIn, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    require_near_today(request, user, body.tested_on)
    profile = latest_profile(db, user)
    # The 14-day spacing applies per level: switching level needs a fresh baseline straight away.
    last = _latest_max_test(db, user, body.exercise, body.level)
    eligibility = max_test_eligibility(
        profile.screening_flags, profile.clearance_confirmed, last.tested_on if last else None, body.tested_on
    )
    if not eligibility.allowed:
        extra = {"next_allowed": eligibility.next_allowed.isoformat()} if eligibility.next_allowed else {}
        raise api_error(409, eligibility.code, eligibility.message, **extra)

    test = MaxTest(user_id=user.id, exercise=body.exercise, reps=body.reps, level=body.level, tested_on=body.tested_on)
    db.add(test)
    db.flush()
    # Reps are sized from the max, so a new max replaces any reps added by weekly reviews.
    week = _progression_for(db, user, body.exercise, body.tested_on, profile, test)
    if week.extra_reps:
        week.extra_reps = 0
        week.note = f"{week.note} Reps re-sized from your new max test."
    db.commit()
    tip = suggest(test.level, test.reps)
    return MaxTestResultOut(
        exercise=test.exercise,
        reps=test.reps,
        level=test.level,
        tested_on=test.tested_on,
        suggestion=LevelSuggestionOut(direction=tip.direction, level=tip.level, message=tip.message) if tip else None,
    )


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
    week = _progression_for(db, user, body.exercise, body.date, profile, max_test)

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
            level=max_test.level,
            extra_sets=week.extra_sets,
            extra_reps=week.extra_reps,
            progression_note=week.note if week.decision in CHANGES else None,
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
        level=plan.level,
        load=plan.load,
        engine_version=plan.engine_version,
        profile_version=profile.version,
        source="server",
    )
    db.add(row)
    db.commit()
    response.status_code = 201
    return row


# Review outcomes that change the plan, and so are worth mentioning in its reason.
CHANGES = {"up_sets", "up_reps", "down_sets", "down_reps", "at_ceiling"}


def _progression_for(
    db: Session, user: User, exercise: str, day: dt.date, profile: Profile, max_test: MaxTest
) -> Progression:
    """This week's progression, reviewing last week first if this is the week's first visit."""
    start = week_start(day)
    row = db.scalar(
        select(Progression).where(
            Progression.user_id == user.id, Progression.exercise == exercise, Progression.week_start == start
        )
    )
    if row is not None:
        return row

    previous = db.scalar(
        select(Progression)
        .where(Progression.user_id == user.id, Progression.exercise == exercise, Progression.week_start < start)
        .order_by(Progression.week_start.desc())
        .limit(1)
    )
    current = (
        ProgressionState(previous.extra_sets, previous.extra_reps, previous.last_step)
        if previous
        else ProgressionState()
    )
    experience = experience_for(profile.training_months)
    base_sets, set_limit = set_limits(
        experience, profile.prompt_limit, to_minutes(profile.window_end) - to_minutes(profile.window_start)
    )
    review = review_week(
        _week_stats(db, user, exercise, start - dt.timedelta(days=7)),
        current,
        base_sets=base_sets,
        set_limit=set_limit,
        base_reps=base_reps_for(experience, max_test.reps),
        max_reps=max_test.reps,
    )
    row = Progression(
        user_id=user.id,
        exercise=exercise,
        week_start=start,
        extra_sets=review.progression.extra_sets,
        extra_reps=review.progression.extra_reps,
        last_step=review.progression.last_step,
        decision=review.decision,
        note=review.note,
    )
    db.add(row)
    db.flush()
    return row


def _week_stats(db: Session, user: User, exercise: str, start: dt.date) -> WeekStats:
    """Planned and done sets for the week from `start`. Days stopped for pain are left out:
    stopping for pain is a safety rule, not a sign the plan was too hard."""
    end = start + dt.timedelta(days=6)
    plans = db.scalars(
        select(Plan).where(
            Plan.user_id == user.id,
            Plan.exercise == exercise,
            Plan.kind == "training",
            Plan.date >= start,
            Plan.date <= end,
        )
    ).all()
    logs = db.scalars(
        select(SetLog).where(
            SetLog.user_id == user.id, SetLog.exercise == exercise, SetLog.date >= start, SetLog.date <= end
        )
    ).all()
    pain_days = {log.date for log in logs if log.rating == "pain"}
    days = [p for p in plans if p.date not in pain_days]
    counted = {p.date for p in days}
    done = [log for log in logs if log.date in counted and log.rating not in ("skipped", "pain") and log.done_reps > 0]
    return WeekStats(
        training_days=len(days),
        sets_planned=sum(len(p.sets) for p in days),
        sets_done=len(done),
        hard_sets=sum(1 for log in done if log.rating == "hard"),
    )


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
        level=body.level,
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
        streak=_streak(db, user, exercise, user_today(request, user)),
    )


@router.get("/streak", response_model=StreakOut)
def get_streak(
    request: Request, exercise: str = "pushup", user: User = Depends(current_user), db: Session = Depends(get_db)
):
    return _streak(db, user, exercise, user_today(request, user))


def _streak(db: Session, user: User, exercise: str, today: dt.date) -> StreakOut:
    """Builds one record per day the user had a plan or logged sets. See engine/streak.py."""
    kinds = dict(db.execute(select(Plan.date, Plan.kind).where(Plan.user_id == user.id, Plan.exercise == exercise)).all())
    logs = db.execute(
        select(SetLog.date, SetLog.done_reps, SetLog.rating).where(SetLog.user_id == user.id, SetLog.exercise == exercise)
    ).all()
    sets_done: dict[dt.date, int] = {}
    pain: set[dt.date] = set()
    for day, done_reps, rating in logs:
        if rating != "skipped" and done_reps > 0:
            sets_done[day] = sets_done.get(day, 0) + 1
        if rating == "pain":
            pain.add(day)
    days = set(kinds) | set(sets_done) | pain
    streak = compute_streak(
        [DayRecord(day, kinds.get(day), sets_done.get(day, 0), day in pain) for day in days], today
    )
    return StreakOut(
        current=streak.current,
        best=streak.best,
        today_on_plan=streak.today_on_plan,
        rest_pass_available=streak.rest_pass_available,
        rest_pass_days=streak.rest_pass_days,
    )
