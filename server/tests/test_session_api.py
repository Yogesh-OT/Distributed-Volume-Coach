import datetime as dt
import uuid

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from tests.test_api import ALICE, ONBOARDING, PROFILE, Clock

MONDAY = dt.date(2026, 10, 5)
SETTINGS = {"goal": "muscle", "days_per_week": 3, "session_minutes": 30}


@pytest.fixture
def clock():
    return Clock(MONDAY)


@pytest.fixture
def c(clock):
    settings = Settings(database_url="sqlite://", auth_mode="dev", create_tables=True)
    with TestClient(create_app(settings, clock=clock)) as client:
        assert client.post("/v1/onboarding", json=ONBOARDING, headers=ALICE).status_code == 201
        client.post("/v1/max-tests", json={"reps": 20, "tested_on": "2026-10-05"}, headers=ALICE)
        yield client


def setup(c, **overrides):
    r = c.put("/v1/session-settings", json={**SETTINGS, **overrides}, headers=ALICE)
    assert r.status_code == 200, r.text
    return r.json()


def start(c, day, **answers):
    return c.post("/v1/sessions", json={"date": day.isoformat(), **answers}, headers=ALICE)


def set_log(day, ex, number, done, effort="good", tested=False, pain=False):
    return {
        "id": str(uuid.uuid4()),
        "date": day.isoformat(),
        "ladder": ex["ladder"],
        "exercise_key": ex["key"],
        "level": ex["level"],
        "set_number": number,
        "target": ex["target"],
        "done": done,
        "effort": effort,
        "tested": tested,
        "pain": pain,
        "logged_at": f"{day.isoformat()}T18:00:00+05:30",
    }


def do_everything(c, day, session, effort="good"):
    """Log every planned set at its target; the last set of each exercise reaches target + 2."""
    logs = []
    for pair in session["payload"]["pairs"]:
        for ex in pair:
            for n in range(1, ex["sets"] + 1):
                last = n == ex["sets"] and ex["test_last_set"]
                logs.append(set_log(day, ex, n, ex["target"] + (2 if last else 0), effort, tested=last))
    assert c.post("/v1/session-logs/batch", json={"logs": logs}, headers=ALICE).status_code == 200
    return c.post(f"/v1/sessions/{day.isoformat()}/complete", json={"finished": True}, headers=ALICE).json()


def exercise(session, ladder):
    return next(ex for pair in session["payload"]["pairs"] for ex in pair if ex["ladder"] == ladder)


def test_settings_come_first(c):
    assert start(c, MONDAY).json()["detail"]["code"] == "session_settings_required"
    saved = setup(c)
    assert saved["weekdays"] == [0, 2, 4] and "table" not in saved["available"]
    states = {s["ladder"]: s for s in c.get("/v1/exercise-states", headers=ALICE).json()}
    assert (states["push"]["level"], states["push"]["target"]) == (4, 14)  # 70% of the 20-rep max
    assert states["row"]["name"] == "Doorway row"


def test_library_is_public():
    with TestClient(create_app(Settings(database_url="sqlite://", auth_mode="dev", create_tables=True))) as client:
        lib = client.get("/v1/exercises").json()
    assert {lad["key"] for lad in lib["ladders"]} >= {"push", "row", "squat"}
    assert lib["ladders"][0]["exercises"][0]["needs"] == ["wall"]


def test_a_session_from_start_to_progress(c, clock):
    setup(c)
    first = start(c, MONDAY, sleep_quality=4, soreness=2, energy=4)
    assert first.status_code == 201
    session = first.json()
    assert session["template"] == "A" and session["readiness"] == 0.75
    assert start(c, MONDAY).json() == session  # one session a day
    assert c.get(f"/v1/sessions/{MONDAY}", headers=ALICE).json() == session

    push = exercise(session, "push")
    logs = [set_log(MONDAY, push, 1, 14), set_log(MONDAY, push, 2, 14), set_log(MONDAY, push, 3, 17, tested=True)]
    r = c.post("/v1/session-logs/batch", json={"logs": logs + logs[:1]}, headers=ALICE).json()
    assert r == {"accepted": 3, "duplicates": 1}

    summary = c.post(f"/v1/sessions/{MONDAY}/complete", json={"finished": False, "quit_reason": "no_time"}, headers=ALICE).json()
    steps = {s["ladder"]: s for s in summary["steps"]}
    assert steps["push"]["decision"] == "up_reps" and steps["row"]["decision"] == "skipped"
    assert summary["sets_done"] == 3
    again = c.post(f"/v1/sessions/{MONDAY}/complete", json={"finished": True}, headers=ALICE).json()
    assert again == summary  # completing twice never progresses twice

    states = {s["ladder"]: s for s in c.get("/v1/exercise-states", headers=ALICE).json()}
    assert states["push"]["target"] == 15

    clock.set(MONDAY + dt.timedelta(days=2))
    assert start(c, MONDAY + dt.timedelta(days=2)).json()["template"] == "B"  # A was done, B is next


def test_pain_pauses_an_exercise_until_resumed(c, clock):
    setup(c)
    session = start(c, MONDAY).json()
    push = exercise(session, "push")
    c.post("/v1/session-logs/batch", json={"logs": [set_log(MONDAY, push, 1, 5, pain=True)]}, headers=ALICE)
    summary = c.post(f"/v1/sessions/{MONDAY}/complete", json={"finished": False, "quit_reason": "pain"}, headers=ALICE).json()
    assert summary["steps"][0]["decision"] == "pain"

    clock.set(MONDAY + dt.timedelta(days=1))
    later = start(c, MONDAY + dt.timedelta(days=1)).json()
    assert "push" not in {ex["ladder"] for pair in later["payload"]["pairs"] for ex in pair}
    resumed = c.put("/v1/exercise-states/push", json={"paused": False}, headers=ALICE).json()
    assert resumed["paused"] is False


def test_switching_level_resets_the_target(c):
    setup(c)
    state = c.put("/v1/exercise-states/push", json={"level": 3}, headers=ALICE).json()
    assert (state["name"], state["target"]) == ("Knee push-up", 6)
    assert c.put("/v1/exercise-states/push", json={"level": 9}, headers=ALICE).status_code == 422


def test_a_strong_week_adds_a_set(c, clock):
    setup(c, session_minutes=45)  # room to grow: 45-minute sessions aren't full at the start
    for offset in (0, 2, 4):
        day = MONDAY + dt.timedelta(days=offset)
        clock.set(day)
        do_everything(c, day, start(c, day).json())
    next_monday = MONDAY + dt.timedelta(days=7)
    clock.set(next_monday)
    session = start(c, next_monday).json()
    assert session["volume_step"] == 1
    assert any("One more set" in note for note in session["payload"]["notes"])


def test_report(c, clock):
    setup(c)
    c.post("/v1/body-measurements", json={"measured_on": "2026-10-05", "weight_kg": 70, "waist_cm": 80}, headers=ALICE)
    for offset in (0, 2, 4):
        day = MONDAY + dt.timedelta(days=offset)
        clock.set(day)
        do_everything(c, day, start(c, day).json())
    report = c.get("/v1/report", headers=ALICE).json()
    assert report["sessions_done"] == 3 and report["sessions_planned"] == 3
    assert report["week_streak"] == 1 and report["minutes"] >= 80
    muscles = {m["muscle"]: m["sets"] for m in report["muscles"]}
    assert 8 <= muscles["chest"] <= 12
    push = next(e for e in report["exercises"] if e["state"]["ladder"] == "push")
    # Test sets reach target + 2: 16, then 17 at the top of the range, which moves up to decline push-ups.
    assert [(h["level"], h["best"]) for h in push["history"]] == [(4, 16), (4, 17), (5, 8)]
    assert report["weights"][0]["weight_kg"] == 70 and report["waists"][0]["waist_cm"] == 80


def test_coming_back_after_a_break(c, clock):
    setup(c)
    do_everything(c, MONDAY, start(c, MONDAY).json())
    before = {s["ladder"]: s["target"] for s in c.get("/v1/exercise-states", headers=ALICE).json()}
    later = MONDAY + dt.timedelta(days=16)
    clock.set(later)
    session = start(c, later).json()
    assert session["payload"]["notes"][0].startswith("Welcome back after 16 days")
    after = {s["ladder"]: s["target"] for s in c.get("/v1/exercise-states", headers=ALICE).json()}
    assert after["push"] < before["push"]


def test_logs_need_a_session(c):
    setup(c)
    fake = {"ladder": "push", "key": "pushup_full", "level": 4, "target": 10}
    r = c.post("/v1/session-logs/batch", json={"logs": [set_log(MONDAY, fake, 1, 10)]}, headers=ALICE)
    assert r.status_code == 409


def test_screening_blocks_sessions_until_cleared(c):
    setup(c)
    c.put("/v1/profile", json={**PROFILE, "screening_flags": ["chest_pain"]}, headers=ALICE)
    assert start(c, MONDAY).json()["detail"]["code"] == "clearance_required"


def test_export_reset_and_delete_cover_sessions(c):
    setup(c)
    do_everything(c, MONDAY, start(c, MONDAY).json())
    export = c.get("/v1/me/export", headers=ALICE).json()
    assert len(export["session_plans"]) == 1 and export["session_set_logs"] and export["exercise_states"]
    assert c.delete(f"/v1/dev/days/{MONDAY}", headers=ALICE).status_code == 204
    assert c.get(f"/v1/sessions/{MONDAY}", headers=ALICE).status_code == 404
    assert c.delete("/v1/me", headers=ALICE).status_code == 204
