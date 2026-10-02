import json
from pathlib import Path

import pytest

from engine.plan import PlannedSet, Policy
from engine.policy import LoggedSet, Rating, apply_logs

VECTORS = json.loads((Path(__file__).parents[2] / "shared" / "policy_vectors.json").read_text(encoding="utf-8"))


def _policy(case: dict) -> Policy:
    return Policy.from_dict({**VECTORS["default_policy"], **case.get("policy_overrides", {})})


@pytest.mark.parametrize("case", VECTORS["cases"], ids=lambda c: c["name"])
def test_policy_vector(case):
    sets = [PlannedSet(**s) for s in case["sets"]]
    logs = [LoggedSet(ref=log["ref"], rating=Rating(log["rating"]), at=log["at"]) for log in case["logs"]]

    day = apply_logs(sets, _policy(case), logs)

    expected = case["expected"]
    assert day.status == expected["status"]
    assert day.hard_sets == expected["hard_sets"]
    actual = [
        {"ref": s.ref, "at": s.at, "target_reps": s.target_reps, "status": s.status, "rating": s.rating}
        for s in day.sets
    ]
    assert actual == expected["sets"]


def test_vectors_cover_every_rating_and_day_status():
    ratings = {log["rating"] for case in VECTORS["cases"] for log in case["logs"]}
    statuses = {case["expected"]["status"] for case in VECTORS["cases"]}
    assert ratings == {r.value for r in Rating}
    assert statuses == {"active", "complete", "ended_hard", "stopped_pain"}
