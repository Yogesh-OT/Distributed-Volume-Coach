from datetime import date

from engine.body import BodyInput, body_profile
from engine.progress import LogRow, daily_summary
from engine.safety import is_adult, max_test_eligibility


def _lines(**kwargs):
    return {line.key: line for line in body_profile(BodyInput(**kwargs))}


def test_sample_body_profile_matches_the_architecture_page():
    lines = _lines(height_cm=172, weight_kg=68, arm_span_cm=178, waist_cm=80, wrist_cm=16.8)

    assert lines["size"].label == "172 cm · 68 kg"
    assert lines["ape_index"].headline == "Long arms for your height (1.03)"
    assert lines["waist_ratio"].headline == "0.47 of your height"
    assert lines["waist_ratio"].detail == "Under the usual 0.5 guide."
    assert lines["frame"].headline == "Medium frame"


def test_frame_without_sex_gives_a_range_when_the_tables_disagree():
    # 172 / 17.5 = 9.83: medium on the male table, large on the female table.
    lines = _lines(height_cm=172, wrist_cm=17.5)
    assert lines["frame"].headline == "Medium to large frame"
    assert "Add sex" in lines["frame"].detail
    assert _lines(height_cm=172, wrist_cm=17.5, sex="female")["frame"].headline == "Large frame"


def test_missing_height_gives_no_ratios():
    assert body_profile(BodyInput(weight_kg=70, arm_span_cm=180)) == []


def test_profile_never_mentions_somatotypes():
    text = " ".join(
        f"{line.headline} {line.detail}"
        for line in body_profile(BodyInput(height_cm=180, weight_kg=90, arm_span_cm=170, waist_cm=115, wrist_cm=20))
    ).lower()
    for word in ("ectomorph", "mesomorph", "endomorph", "body type"):
        assert word not in text


def test_screening_flags_block_max_tests_until_cleared():
    today = date(2026, 10, 5)
    blocked = max_test_eligibility(["chest_pain"], False, None, today)
    assert not blocked.allowed and blocked.code == "clearance_required"
    assert max_test_eligibility(["chest_pain"], True, None, today).allowed


def test_max_tests_are_14_days_apart():
    today = date(2026, 10, 5)
    too_soon = max_test_eligibility([], False, date(2026, 9, 22), today)
    assert too_soon.code == "too_soon" and too_soon.next_allowed == date(2026, 10, 6)
    assert max_test_eligibility([], False, date(2026, 9, 21), today).allowed


def test_adult_check_needs_year_and_confirmation():
    today = date(2026, 10, 5)
    assert is_adult(2008, today, True)
    assert not is_adult(2008, today, False)
    assert not is_adult(2009, today, True)


def test_daily_summary_counts_done_sets_and_hard_sets():
    d1, d2 = date(2026, 10, 5), date(2026, 10, 6)
    rows = [
        LogRow(d1, 9, "easy"),
        LogRow(d1, 9, "hard"),
        LogRow(d1, 0, "skipped"),
        LogRow(d2, 0, "skipped"),
    ]
    summary = daily_summary(rows)
    assert [(s.day, s.sets_done, s.reps_done, s.hard_sets) for s in summary] == [(d1, 2, 18, 1), (d2, 0, 0, 0)]
