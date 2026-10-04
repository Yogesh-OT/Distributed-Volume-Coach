"""Session mode: settings, today's session, set logs, progression after a session, and the report.

The rules live in engine/sessions.py, engine/session_progression.py and engine/report.py;
this module only loads and stores rows.
"""

import datetime as dt

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from engine import ENGINE_VERSION
from engine.common import experience_for
from engine.exercises import CARDIO_MOVES, CIRCUIT_LEVELS, LADDERS, MAJOR_MUSCLES, ExerciseState, Muscle, Need, ladder
from engine.progression import week_start
from engine.readiness import readiness
from engine.report import logged_muscle_sets, week_streak, weekly_weight_change
from engine.safety import max_test_eligibility
from engine.session_progression import (
    BREAK_DAYS,
    CircuitRating,
    Effort,
    SessionWeek,
    SetResult,
    after_break,
    after_circuit,
    after_session,
    review_volume,
)
from engine.sessions import Goal, SessionInput, build_session, initial_states, rotation, session_to_dict

from ..auth import current_user
from ..db import get_db
from ..errors import api_error
from ..models import (
    BodyMeasurement,
    ExerciseStateRow,
    MaxTest,
    SessionPlan,
    SessionReview,
    SessionSetLog,
    SessionSettings,
    User,
)
from ..schemas import (
    ExerciseHistoryOut,
    ExerciseProgressOut,
    ExerciseStateIn,
    ExerciseStateOut,
    MuscleSetsOut,
    ReportOut,
    SessionCompleteIn,
    SessionLogBatchIn,
    SessionOut,
    SessionSettingsIn,
    SessionSettingsOut,
    SessionStartIn,
    SessionSummaryOut,
    SetLogBatchOut,
    StepOut,
    WaistOut,
    WeekSummaryOut,
    WeightOut,
)
from ..timeutil import require_near_today, user_today
from .profile import latest_profile

router = APIRouter(prefix="/v1", tags=["sessions"])
CIRCUIT_ROW = "circuit"  # the exercise_states row that holds the circuit level
FULL_WITHIN_MIN = 3  # a session this close to its chosen length counts as full


@router.get("/exercises")
def exercise_library():
    """The whole library, for how-to screens and offline use. The same for everyone."""
    return {
        "ladders": [
            {
                "key": lad.key,
                "title": lad.title,
                "unit": str(lad.unit),
                "rep_range": lad.rep_range,
                "step": lad.step,
                "muscles": {str(m): w for m, w in lad.muscles.items()},
                "exercises": [
                    {
                        "key": ex.key,
                        "name": ex.name,
                        "level": ex.level,
                        "cue": ex.cue,
                        "each_side": ex.each_side,
                        "needs": [str(n) for n in ex.needs],
                        "rep_range": lad.range_for(ex.level),
                        "test_last_set": ex.test_last_set,
                    }
                    for ex in lad.exercises
                ],
            }
            for lad in LADDERS.values()
        ],
        "cardio_moves": [vars(m) for m in CARDIO_MOVES],
        "circuit_levels": [vars(c) for c in CIRCUIT_LEVELS],
    }


# --- settings and exercise states ---


def _settings(db: Session, user: User) -> SessionSettings:
    row = db.scalar(select(SessionSettings).where(SessionSettings.user_id == user.id))
    if row is None:
        raise api_error(409, "session_settings_required", "Choose your goal, days and session length first.")
    return row


def _available(settings: SessionSettings) -> frozenset[Need]:
    return frozenset(Need(n) for n in settings.available)


def _state_rows(db: Session, user: User) -> dict[str, ExerciseStateRow]:
    rows = db.scalars(select(ExerciseStateRow).where(ExerciseStateRow.user_id == user.id)).all()
    return {r.ladder: r for r in rows}


def _state(row: ExerciseStateRow) -> ExerciseState:
    return ExerciseState(row.ladder, row.level, row.target, row.below_range)


def _state_out(row: ExerciseStateRow) -> ExerciseStateOut:
    lad = ladder(row.ladder)
    ex = lad.at(row.level)
    return ExerciseStateOut(
        ladder=row.ladder,
        title=lad.title,
        level=row.level,
        name=ex.name,
        target=row.target,
        unit=str(lad.unit),
        rep_range=lad.range_for(row.level),
        each_side=ex.each_side,
        paused=row.paused,
    )


@router.get("/session-settings", response_model=SessionSettingsOut)
def get_session_settings(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return _settings(db, user)


@router.put("/session-settings", response_model=SessionSettingsOut)
def put_session_settings(
    body: SessionSettingsIn, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    """Saves the settings. The first time, every exercise gets a starting level; later
    changes keep the levels already reached."""
    row = db.scalar(select(SessionSettings).where(SessionSettings.user_id == user.id))
    if row is None:
        row = SessionSettings(user_id=user.id)
        db.add(row)
    for field, value in body.model_dump().items():
        setattr(row, field, value)
    row.updated_at = request.app.state.clock()

    existing = _state_rows(db, user)
    profile = latest_profile(db, user)
    push = db.scalar(
        select(MaxTest)
        .where(MaxTest.user_id == user.id, MaxTest.exercise == "pushup")
        .order_by(MaxTest.tested_on.desc(), MaxTest.id.desc())
        .limit(1)
    )
    states = initial_states(
        experience_for(profile.training_months),
        frozenset(Need(n) for n in body.available),
        push_max=push.reps if push else None,
        push_level=push.level if push else None,
    )
    for key, state in states.items():
        if key not in existing:
            db.add(ExerciseStateRow(user_id=user.id, ladder=key, level=state.level, target=state.target))
    if CIRCUIT_ROW not in existing:
        db.add(ExerciseStateRow(user_id=user.id, ladder=CIRCUIT_ROW, level=1, target=0))
    db.commit()
    return row


@router.get("/exercise-states", response_model=list[ExerciseStateOut])
def get_exercise_states(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = _state_rows(db, user)
    return [_state_out(rows[k]) for k in LADDERS if k in rows]


@router.put("/exercise-states/{ladder_key}", response_model=ExerciseStateOut)
def put_exercise_state(
    ladder_key: str, body: ExerciseStateIn, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    """Switch to an easier or harder version, or resume an exercise paused for pain."""
    row = _state_rows(db, user).get(ladder_key)
    if row is None or ladder_key not in LADDERS:
        raise api_error(404, "unknown_exercise", "There's no such exercise in your plan.")
    lad = ladder(ladder_key)
    if body.level is not None:
        if body.level > len(lad.exercises):
            raise api_error(422, "level_out_of_range", f"{lad.title} has levels 1-{len(lad.exercises)}.")
        if body.level != row.level:
            row.level, row.target, row.below_range = body.level, lad.range_for(body.level)[0], 0
    if body.paused is not None:
        row.paused = body.paused
    db.commit()
    return _state_out(row)


# --- today's session ---


def _find_session(db: Session, user: User, day: dt.date) -> SessionPlan | None:
    return db.scalar(select(SessionPlan).where(SessionPlan.user_id == user.id, SessionPlan.date == day))


def _done_session_ids(db: Session, user: User) -> set[int]:
    """Sessions that actually happened: at least one set logged, or a finished circuit."""
    logged = set(db.scalars(select(SessionSetLog.session_id).where(SessionSetLog.user_id == user.id)))
    finished = set(
        db.scalars(select(SessionPlan.id).where(SessionPlan.user_id == user.id, SessionPlan.finished.is_(True)))
    )
    return logged | finished


@router.post("/sessions", response_model=SessionOut)
def start_session(
    body: SessionStartIn,
    request: Request,
    response: Response,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Builds today's session, or returns it if it already exists."""
    require_near_today(request, user, body.date)
    existing = _find_session(db, user, body.date)
    if existing is not None:
        return existing

    settings = _settings(db, user)
    profile = latest_profile(db, user)
    if profile.screening_flags and not profile.clearance_confirmed:
        check = max_test_eligibility(profile.screening_flags, False, None, body.date)
        raise api_error(409, check.code, check.message)
    available = _available(settings)
    rows = _state_rows(db, user)
    notes = []

    done_ids = _done_session_ids(db, user)
    last_day = db.scalar(
        select(SessionPlan.date)
        .where(SessionPlan.user_id == user.id, SessionPlan.id.in_(done_ids), SessionPlan.date < body.date)
        .order_by(SessionPlan.date.desc())
        .limit(1)
    )
    if last_day is not None and (body.date - last_day).days >= BREAK_DAYS:
        days_off = (body.date - last_day).days
        for key, row in rows.items():
            if key in LADDERS:
                new = after_break(_state(row), days_off, available)
                row.level, row.target, row.below_range = new.level, new.target, new.below_range
        notes.append(f"Welcome back after {days_off} days. Targets are lighter for now.")

    review = _review_for(db, user, body.date, settings)
    if review.decision in ("up", "down", "at_ceiling"):
        notes.append(review.note)

    score = None
    if body.sleep_quality is not None:
        score = round(readiness(body.sleep_quality, body.soreness, body.energy), 2)
    goal = Goal(settings.goal)
    session = build_session(
        SessionInput(
            goal=goal,
            slot=rotation(goal, settings.days_per_week, len(done_ids)),
            minutes=settings.session_minutes,
            states={k: _state(r) for k, r in rows.items() if k in LADDERS},
            available=available,
            volume_step=review.volume_step,
            readiness=score,
            circuit_level=rows[CIRCUIT_ROW].level if CIRCUIT_ROW in rows else 1,
            high_impact=settings.high_impact,
            seed=f"{user.id}:{body.date.isoformat()}",
            paused=frozenset(k for k, r in rows.items() if r.paused),
        )
    )
    payload = session_to_dict(session)
    payload["notes"] = notes
    row = SessionPlan(
        user_id=user.id,
        date=body.date,
        template=session.template,
        goal=settings.goal,
        minutes=session.minutes,
        volume_step=review.volume_step,
        sleep_quality=body.sleep_quality,
        soreness=body.soreness,
        energy=body.energy,
        readiness=score,
        payload=payload,
        engine_version=ENGINE_VERSION,
    )
    db.add(row)
    db.commit()
    response.status_code = 201
    return row


def _review_for(db: Session, user: User, day: dt.date, settings: SessionSettings) -> SessionReview:
    """This week's volume step, reviewing last week first if this is the week's first session."""
    start = week_start(day)
    row = db.scalar(select(SessionReview).where(SessionReview.user_id == user.id, SessionReview.week_start == start))
    if row is not None:
        return row
    previous = db.scalar(
        select(SessionReview)
        .where(SessionReview.user_id == user.id, SessionReview.week_start < start)
        .order_by(SessionReview.week_start.desc())
        .limit(1)
    )
    last = start - dt.timedelta(days=7)
    plans = db.scalars(
        select(SessionPlan).where(SessionPlan.user_id == user.id, SessionPlan.date >= last, SessionPlan.date < start)
    ).all()
    logs = db.scalars(
        select(SessionSetLog).where(
            SessionSetLog.user_id == user.id, SessionSetLog.date >= last, SessionSetLog.date < start
        )
    ).all()
    logged_ids = {log.session_id for log in logs}
    done_plans = [p for p in plans if p.id in logged_ids]
    done = [log for log in logs if log.done > 0 and not log.pain]
    regular = [log for log in done if not log.tested]
    soreness = [p.soreness for p in plans if p.soreness is not None]
    muscles = logged_muscle_sets(log.ladder for log in done)
    review = review_volume(
        SessionWeek(
            sessions_done=len(done_plans),
            sets_planned=sum(p.payload.get("total_sets", 0) for p in done_plans),
            sets_done=len(done),
            regular_sets=len(regular),
            maxed_sets=sum(1 for log in regular if log.effort == Effort.MAX),
            avg_soreness=sum(soreness) / len(soreness) if soreness else None,
            most_muscle_sets=max(muscles[m] for m in MAJOR_MUSCLES),
            sessions_full=bool(done_plans)
            and all(p.minutes >= settings.session_minutes - FULL_WITHIN_MIN for p in done_plans),
        ),
        previous.volume_step if previous else 0,
    )
    row = SessionReview(
        user_id=user.id, week_start=start, volume_step=review.step, decision=review.decision, note=review.note
    )
    db.add(row)
    db.flush()
    return row


@router.get("/sessions/{day}", response_model=SessionOut)
def get_session(day: dt.date, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = _find_session(db, user, day)
    if row is None:
        raise api_error(404, "no_session", "There's no session for that day.")
    return row


@router.post("/session-logs/batch", response_model=SetLogBatchOut)
def upload_session_logs(body: SessionLogBatchIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    unique = {str(log.id): log for log in body.logs}  # repeats inside one batch count once
    already = set(db.scalars(select(SessionSetLog.id).where(SessionSetLog.id.in_(list(unique)))))
    sessions: dict[dt.date, SessionPlan] = {}
    for log_id, log in unique.items():
        if log_id in already:
            continue
        if log.date not in sessions:
            plan = _find_session(db, user, log.date)
            if plan is None:
                raise api_error(409, "no_session", f"There's no session on {log.date} to log sets against.")
            sessions[log.date] = plan
        db.add(
            SessionSetLog(
                id=log_id,
                user_id=user.id,
                session_id=sessions[log.date].id,
                date=log.date,
                ladder=log.ladder,
                exercise_key=log.exercise_key,
                level=log.level,
                set_number=log.set_number,
                target=log.target,
                done=log.done,
                effort=log.effort,
                tested=log.tested,
                pain=log.pain,
                logged_at=log.logged_at,
            )
        )
    db.commit()
    accepted = len(unique) - len(already)
    return SetLogBatchOut(accepted=accepted, duplicates=len(body.logs) - accepted)


@router.post("/sessions/{day}/complete", response_model=SessionSummaryOut)
def complete_session(
    day: dt.date,
    body: SessionCompleteIn,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Runs one progression step per exercise. Completing again returns the same summary."""
    plan = _find_session(db, user, day)
    if plan is None:
        raise api_error(404, "no_session", "There's no session for that day.")
    if plan.completed_at is not None:
        return plan.summary

    available = _available(_settings(db, user))
    rows = _state_rows(db, user)
    logs = db.scalars(
        select(SessionSetLog)
        .where(SessionSetLog.session_id == plan.id)
        .order_by(SessionSetLog.set_number, SessionSetLog.logged_at)
    ).all()
    steps = []
    for pair in plan.payload["pairs"]:
        for ex in pair:
            key = ex["ladder"]
            row = rows.get(key)
            if row is None:
                continue
            mine = [log for log in logs if log.ladder == key]
            # Score the version actually done, in case it was switched mid-session.
            state = ExerciseState(key, mine[0].level, mine[0].target, row.below_range) if mine else _state(row)
            step = after_session(
                state,
                [SetResult(log.done, Effort(log.effort), log.pain) for log in mine],
                tested=bool(mine) and mine[-1].tested,
                available=available,
            )
            row.level, row.target, row.below_range = step.state.level, step.state.target, step.state.below_range
            if step.decision == "pain":
                row.paused = True
            steps.append(StepOut(ladder=key, decision=step.decision, note=step.note))

    circuit_note = None
    circuit = rows.get(CIRCUIT_ROW)
    if plan.payload.get("circuit") and body.circuit_rating and circuit is not None:
        previous = CircuitRating(circuit.last_rating) if circuit.last_rating else None
        circuit.level, circuit_note = after_circuit(
            circuit.level, CircuitRating(body.circuit_rating), previous, body.finished
        )
        circuit.last_rating = body.circuit_rating

    summary = SessionSummaryOut(
        date=day,
        finished=body.finished,
        sets_done=sum(1 for log in logs if log.done > 0),
        steps=steps,
        circuit_note=circuit_note,
    )
    plan.completed_at = request.app.state.clock()
    plan.finished = body.finished
    plan.quit_reason = body.quit_reason
    plan.summary = summary.model_dump(mode="json")
    db.commit()
    return summary


# --- the report ---


@router.get("/report", response_model=ReportOut)
def get_report(
    request: Request,
    weeks: int = Query(default=8, ge=1, le=52),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    settings = _settings(db, user)
    today = user_today(request, user)
    this_week = week_start(today)
    since = this_week - dt.timedelta(days=7 * (weeks - 1))
    plans = db.scalars(
        select(SessionPlan).where(SessionPlan.user_id == user.id, SessionPlan.date >= since).order_by(SessionPlan.date)
    ).all()
    logs = db.scalars(
        select(SessionSetLog)
        .where(SessionSetLog.user_id == user.id, SessionSetLog.date >= since)
        .order_by(SessionSetLog.date, SessionSetLog.set_number)
    ).all()
    done = [log for log in logs if log.done > 0 and not log.pain]
    done_ids = {log.session_id for log in logs} | {p.id for p in plans if p.finished}

    sessions_by_week: dict[dt.date, list[SessionPlan]] = {}
    for p in plans:
        if p.id in done_ids:
            sessions_by_week.setdefault(week_start(p.date), []).append(p)
    sets_by_week: dict[dt.date, int] = {}
    for log in done:
        sets_by_week[week_start(log.date)] = sets_by_week.get(week_start(log.date), 0) + 1
    current, best = week_streak(
        {w: len(ps) for w, ps in sessions_by_week.items()}, settings.days_per_week, this_week
    )
    muscles = logged_muscle_sets(log.ladder for log in done if log.date >= this_week)

    # One point per exercise per day: the test set if there was one, else the best set.
    history: dict[str, dict[dt.date, ExerciseHistoryOut]] = {}
    for log in done:
        days = history.setdefault(log.ladder, {})
        entry = days.get(log.date)
        if entry is None or log.tested or (log.done > entry.best and not _has_test(done, log)):
            days[log.date] = ExerciseHistoryOut(date=log.date, level=log.level, best=log.done)

    rows = _state_rows(db, user)
    body_rows = db.scalars(
        select(BodyMeasurement).where(BodyMeasurement.user_id == user.id).order_by(BodyMeasurement.measured_on)
    ).all()
    weights = [(b.measured_on, b.weight_kg) for b in body_rows if b.weight_kg is not None]
    this_week_sessions = sessions_by_week.get(this_week, [])
    week_list = [since + dt.timedelta(days=7 * i) for i in range(weeks)]
    return ReportOut(
        week_start=this_week,
        sessions_planned=settings.days_per_week,
        sessions_done=len(this_week_sessions),
        sets_done=sets_by_week.get(this_week, 0),
        minutes=sum(p.minutes for p in this_week_sessions),
        week_streak=current,
        best_week_streak=best,
        muscles=[MuscleSetsOut(muscle=str(m), sets=muscles[m]) for m in Muscle],
        weeks=[
            WeekSummaryOut(week_start=w, sessions=len(sessions_by_week.get(w, [])), sets=sets_by_week.get(w, 0))
            for w in week_list
        ],
        exercises=[
            ExerciseProgressOut(state=_state_out(rows[k]), history=list(history.get(k, {}).values()))
            for k in LADDERS
            if k in rows
        ],
        weights=[WeightOut(measured_on=d, weight_kg=kg) for d, kg in weights],
        waists=[WaistOut(measured_on=b.measured_on, waist_cm=b.waist_cm) for b in body_rows if b.waist_cm is not None],
        weekly_weight_change_pct=weekly_weight_change(weights, today),
    )


def _has_test(logs: list[SessionSetLog], log: SessionSetLog) -> bool:
    return any(o.tested for o in logs if o.ladder == log.ladder and o.date == log.date)
