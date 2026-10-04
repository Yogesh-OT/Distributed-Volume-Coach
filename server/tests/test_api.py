import datetime as dt
import uuid

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

# 07:40 on 5 Oct 2026 in Asia/Kolkata (UTC+5:30).
NOW = dt.datetime(2026, 10, 5, 2, 10, tzinfo=dt.UTC)
TODAY = "2026-10-05"
ALICE = {"Authorization": "Bearer dev:alice"}
BOB = {"Authorization": "Bearer dev:bob"}

PROFILE = {
    "goal": "more_pushups",
    "training_months": 12,
    "wake_time": "07:00",
    "window_start": "09:00",
    "window_end": "19:00",
    "quiet_start": "21:30",
    "quiet_end": "07:00",
    "prompt_limit": 8,
}
ONBOARDING = {
    "timezone": "Asia/Kolkata",
    "birth_year": 1998,
    "confirmed_adult": True,
    "accepted_terms": True,
    "profile": PROFILE,
}
CHECKIN = {"date": TODAY, "local_time": "07:40", "sleep_quality": 4, "soreness": 2, "energy": 4}


@pytest.fixture
def client():
    settings = Settings(database_url="sqlite://", auth_mode="dev", create_tables=True)
    with TestClient(create_app(settings, clock=lambda: NOW)) as c:
        yield c


def onboard(client, headers=ALICE, **overrides):
    return client.post("/v1/onboarding", json={**ONBOARDING, **overrides}, headers=headers)


def ready_to_train(client, headers=ALICE):
    assert onboard(client, headers).status_code == 201
    assert client.post("/v1/max-tests", json={"reps": 20, "tested_on": TODAY}, headers=headers).status_code == 201


def log(set_ref, rating, local_time, done_reps=9, log_id=None):
    return {
        "id": log_id or str(uuid.uuid4()),
        "date": TODAY,
        "set_ref": set_ref,
        "target_reps": 9,
        "done_reps": done_reps,
        "rating": rating,
        "logged_at": f"{TODAY}T{local_time}:00+05:30",
        "local_time": local_time,
    }


def test_full_day(client):
    ready_to_train(client)

    first = client.post("/v1/checkins", json=CHECKIN, headers=ALICE)
    assert first.status_code == 201
    plan = first.json()
    assert plan["source"] == "server"
    assert len(plan["sets"]) == 6 and {s["target_reps"] for s in plan["sets"]} == {9}
    assert plan["reason"] == "Good sleep, good energy and low soreness: 6 sets of 9 push-ups (45% of your 20-rep max)."

    again = client.post("/v1/checkins", json={**CHECKIN, "sleep_quality": 1}, headers=ALICE)
    assert again.status_code == 200 and again.json() == plan  # one plan per day
    assert client.get(f"/v1/plans/{TODAY}", headers=ALICE).json() == plan

    logs = [log("s1", "easy", "09:50"), log("s2", "hard", "11:20")]
    assert client.post("/v1/set-logs/batch", json={"logs": logs}, headers=ALICE).json() == {
        "accepted": 2,
        "duplicates": 0,
    }
    retry = client.post("/v1/set-logs/batch", json={"logs": logs}, headers=ALICE)
    assert retry.json() == {"accepted": 0, "duplicates": 2}

    progress = client.get("/v1/progress", headers=ALICE).json()
    assert progress["max_tests"] == [{"exercise": "pushup", "reps": 20, "level": 4, "tested_on": TODAY}]
    assert progress["days"] == [{"date": TODAY, "sets_done": 2, "reps_done": 18, "hard_sets": 1}]


def test_requests_need_a_token_and_onboarding(client):
    assert client.get("/v1/profile").status_code == 401
    assert client.get("/v1/profile", headers={"Authorization": "Bearer real-looking-token"}).status_code == 401
    response = client.get("/v1/profile", headers=ALICE)
    assert response.status_code == 404 and response.json()["detail"]["code"] == "not_onboarded"


def test_onboarding_rules(client):
    assert onboard(client, birth_year=2009).status_code == 403
    assert onboard(client, confirmed_adult=False).status_code == 403
    assert onboard(client, accepted_terms=False).json()["detail"]["code"] == "terms_required"
    assert onboard(client, timezone="Mars/Olympus").status_code == 422
    overlapping = {**PROFILE, "window_end": "22:00"}
    assert onboard(client, profile=overlapping).status_code == 422
    assert onboard(client).status_code == 201
    assert onboard(client).json()["detail"]["code"] == "already_onboarded"


def test_screening_answers_block_max_tests_until_cleared(client):
    flagged = {**PROFILE, "screening_flags": ["chest_pain"]}
    assert onboard(client, profile=flagged).status_code == 201

    blocked = client.post("/v1/max-tests", json={"reps": 20, "tested_on": TODAY}, headers=ALICE)
    assert blocked.status_code == 409 and blocked.json()["detail"]["code"] == "clearance_required"

    cleared = client.put("/v1/profile", json={**flagged, "clearance_confirmed": True}, headers=ALICE)
    assert cleared.json()["version"] == 2
    assert client.post("/v1/max-tests", json={"reps": 20, "tested_on": TODAY}, headers=ALICE).status_code == 201

    too_soon = client.post("/v1/max-tests", json={"reps": 22, "tested_on": TODAY}, headers=ALICE)
    assert too_soon.status_code == 409
    assert too_soon.json()["detail"]["next_allowed"] == "2026-10-19"


def test_check_in_needs_a_max_test_and_a_date_near_today(client):
    assert onboard(client).status_code == 201
    response = client.post("/v1/checkins", json=CHECKIN, headers=ALICE)
    assert response.status_code == 409 and response.json()["detail"]["code"] == "max_test_required"

    client.post("/v1/max-tests", json={"reps": 20, "tested_on": TODAY}, headers=ALICE)
    stale = client.post("/v1/checkins", json={**CHECKIN, "date": "2026-10-01"}, headers=ALICE)
    assert stale.status_code == 422 and stale.json()["detail"]["code"] == "date_out_of_range"


def test_body_profile_keeps_older_values_when_only_weight_is_sent(client):
    assert onboard(client).status_code == 201
    first = client.post(
        "/v1/body-measurements",
        json={"measured_on": TODAY, "height_cm": 172, "weight_kg": 68, "arm_span_cm": 178, "waist_cm": 80, "wrist_cm": 16.8},
        headers=ALICE,
    )
    assert first.status_code == 201
    headlines = {line["key"]: line["headline"] for line in first.json()["lines"]}
    assert headlines["ape_index"] == "Long arms for your height (1.03)"
    assert headlines["frame"] == "Medium frame"

    client.post("/v1/body-measurements", json={"measured_on": "2026-10-06", "weight_kg": 67, "source": "scale"}, headers=ALICE)
    profile = client.get("/v1/body-profile", headers=ALICE).json()
    assert profile["measured_on"] == "2026-10-06"
    assert profile["lines"][0]["label"] == "172 cm · 67 kg"
    assert client.post("/v1/body-measurements", json={"measured_on": TODAY}, headers=ALICE).status_code == 422


def test_fallback_plan_is_stored_unless_the_server_already_planned(client):
    ready_to_train(client)
    fallback = {
        "date": TODAY,
        "sets": [{"ref": "s1", "at": "10:00", "target_reps": 9}, {"ref": "s2", "at": "12:00", "target_reps": 9}],
        "policy": {"window_end": "19:00"},
        "reason": "Offline: your last plan with one set fewer.",
        "max_reps": 20,
        "load": 0.45,
        "engine_version": "phone-0.1.0",
        "checkin": CHECKIN,
    }
    stored = client.post("/v1/plans/fallback", json=fallback, headers=ALICE)
    assert stored.status_code == 201 and stored.json()["source"] == "fallback"
    assert client.post("/v1/checkins", json=CHECKIN, headers=ALICE).json()["source"] == "fallback"
    assert client.post("/v1/plans/fallback", json=fallback, headers=ALICE).status_code == 200


def test_users_only_see_their_own_data(client):
    ready_to_train(client)
    ready_to_train(client, BOB)
    client.post("/v1/checkins", json=CHECKIN, headers=ALICE)
    assert client.get(f"/v1/plans/{TODAY}", headers=BOB).status_code == 404


def test_export_then_delete_account(client):
    ready_to_train(client)
    ready_to_train(client, BOB)
    client.post("/v1/checkins", json=CHECKIN, headers=ALICE)
    client.post("/v1/set-logs/batch", json={"logs": [log("s1", "solid", "09:50")]}, headers=ALICE)

    export = client.get("/v1/me/export", headers=ALICE).json()
    assert export["user"]["timezone"] == "Asia/Kolkata"
    assert len(export["plans"]) == 1 and len(export["set_logs"]) == 1 and len(export["consents"]) == 1

    assert client.delete("/v1/me", headers=ALICE).status_code == 204
    assert client.get("/v1/profile", headers=ALICE).status_code == 404
    assert client.get("/v1/profile", headers=BOB).status_code == 200
    assert onboard(client).status_code == 201  # the same sign-in can start over


def test_dev_reset_lets_a_day_be_planned_again(client):
    ready_to_train(client)
    ready_to_train(client, BOB)
    client.post("/v1/checkins", json=CHECKIN, headers=ALICE)
    client.post("/v1/checkins", json=CHECKIN, headers=BOB)
    client.post("/v1/set-logs/batch", json={"logs": [log("s1", "solid", "09:50")]}, headers=ALICE)

    assert client.delete(f"/v1/dev/days/{TODAY}", headers=ALICE).status_code == 204
    assert client.get(f"/v1/plans/{TODAY}", headers=ALICE).status_code == 404
    assert client.get("/v1/progress", headers=ALICE).json()["days"] == []

    late = client.post("/v1/checkins", json={**CHECKIN, "local_time": "17:30"}, headers=ALICE)
    assert late.status_code == 201 and len(late.json()["sets"]) == 1  # planned again, from the new check-in
    assert client.get(f"/v1/plans/{TODAY}", headers=BOB).status_code == 200  # other users untouched


def test_dev_routes_do_not_exist_outside_dev_mode():
    settings = Settings(database_url="sqlite://", auth_mode="firebase", create_tables=True)
    with TestClient(create_app(settings, clock=lambda: NOW)) as c:
        assert c.delete(f"/v1/dev/days/{TODAY}", headers=ALICE).status_code == 404


def test_max_tests_carry_a_level_and_a_suggestion(client):
    assert onboard(client).status_code == 201
    weak = client.post("/v1/max-tests", json={"reps": 3, "tested_on": TODAY}, headers=ALICE).json()
    assert weak["level"] == 4 and weak["suggestion"]["direction"] == "down" and weak["suggestion"]["level"] == 3

    # Switching level needs a fresh baseline, so the 14-day spacing doesn't apply to it.
    knee = client.post("/v1/max-tests", json={"reps": 12, "level": 3, "tested_on": TODAY}, headers=ALICE)
    assert knee.status_code == 201 and knee.json()["suggestion"] is None
    again = client.post("/v1/max-tests", json={"reps": 13, "level": 3, "tested_on": TODAY}, headers=ALICE)
    assert again.status_code == 409 and again.json()["detail"]["code"] == "too_soon"

    plan = client.post("/v1/checkins", json=CHECKIN, headers=ALICE).json()
    assert plan["level"] == 3 and plan["max_reps"] == 12
    assert "of 5 knee push-ups (42% of your 12-rep max)" in plan["reason"]  # 5 of 12, the real share


def test_streak_counts_days_on_plan(client):
    ready_to_train(client)
    assert client.get("/v1/streak", headers=ALICE).json()["current"] == 0

    client.post("/v1/checkins", json=CHECKIN, headers=ALICE)
    client.post("/v1/set-logs/batch", json={"logs": [log("s1", "solid", "09:50")]}, headers=ALICE)
    streak = client.get("/v1/streak", headers=ALICE).json()
    assert streak == {
        "current": 1,
        "best": 1,
        "today_on_plan": True,
        "rest_pass_available": True,
        "rest_pass_days": [],
    }
    assert client.get("/v1/progress", headers=ALICE).json()["streak"]["current"] == 1


class Clock:
    """A clock the test can move day by day. Times are 07:40 in Asia/Kolkata."""

    def __init__(self, day: dt.date):
        self.set(day)

    def set(self, day: dt.date):
        self.now = dt.datetime(day.year, day.month, day.day, 2, 10, tzinfo=dt.UTC)

    def __call__(self):
        return self.now


def _train_week(c, monday: dt.date, clock: Clock, rating: str = "solid"):
    """Check in Monday to Friday and log every planned set with `rating`."""
    for offset in range(5):
        day = monday + dt.timedelta(days=offset)
        clock.set(day)
        plan = c.post("/v1/checkins", json={**CHECKIN, "date": day.isoformat()}, headers=ALICE).json()
        logs = [
            {
                **log(s["ref"], rating, s["at"], done_reps=s["target_reps"]),
                "date": day.isoformat(),
                "logged_at": f"{day.isoformat()}T{s['at']}:00+05:30",
            }
            for s in plan["sets"]
        ]
        c.post("/v1/set-logs/batch", json={"logs": logs}, headers=ALICE)
    return plan


def test_strong_week_adds_a_set_next_week():
    monday = dt.date(2026, 9, 28)
    clock = Clock(monday)
    settings = Settings(database_url="sqlite://", auth_mode="dev", create_tables=True)
    with TestClient(create_app(settings, clock=clock)) as c:
        onboard(c)
        c.post("/v1/max-tests", json={"reps": 20, "tested_on": monday.isoformat()}, headers=ALICE)
        week1 = _train_week(c, monday, clock)
        assert len(week1["sets"]) == 6 and "This week" not in week1["reason"]  # first week: baseline

        next_monday = monday + dt.timedelta(days=7)
        clock.set(next_monday)
        week2 = c.post("/v1/checkins", json={**CHECKIN, "date": next_monday.isoformat()}, headers=ALICE).json()
        assert len(week2["sets"]) == 7  # 8 sets before readiness, 7 after it
        assert week2["reason"].endswith("This week: +1 set a day after a strong week (100% done, no hard sets).")


def test_new_max_test_resets_reps_added_by_reviews():
    monday = dt.date(2026, 9, 21)
    clock = Clock(monday)
    settings = Settings(database_url="sqlite://", auth_mode="dev", create_tables=True)
    with TestClient(create_app(settings, clock=clock)) as c:
        onboard(c)
        c.post("/v1/max-tests", json={"reps": 20, "tested_on": monday.isoformat()}, headers=ALICE)
        _train_week(c, monday, clock)  # week 1: baseline
        _train_week(c, monday + dt.timedelta(days=7), clock)  # week 2: +1 set, then trained strongly again
        week3 = monday + dt.timedelta(days=14)
        clock.set(week3)
        plan = c.post("/v1/checkins", json={**CHECKIN, "date": week3.isoformat()}, headers=ALICE).json()
        assert {s["target_reps"] for s in plan["sets"]} == {10}  # +1 rep this week
        assert "+1 rep per set" in plan["reason"]

        c.delete(f"/v1/dev/days/{week3.isoformat()}", headers=ALICE)
        c.post("/v1/max-tests", json={"reps": 24, "tested_on": week3.isoformat()}, headers=ALICE)
        replanned = c.post("/v1/checkins", json={**CHECKIN, "date": week3.isoformat()}, headers=ALICE).json()
        assert {s["target_reps"] for s in replanned["sets"]} == {11}  # 45% of 24, no extra rep
