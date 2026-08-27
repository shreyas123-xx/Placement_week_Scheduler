import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.scheduling_engine import CompanyInput, schedule_day
from app.core.timeutil import minute_to_slot, duration_to_slots


def test_no_double_booking_small_case():
    """3 companies, overlapping shortlists, tight room supply."""
    companies = [
        CompanyInput(id=1, day=1, window_start_min=540, window_end_min=600,
                     interview_duration_min=15, panel_ids=[101]),
        CompanyInput(id=2, day=1, window_start_min=540, window_end_min=600,
                     interview_duration_min=15, panel_ids=[201]),
        CompanyInput(id=3, day=1, window_start_min=540, window_end_min=600,
                     interview_duration_min=15, panel_ids=[301, 302]),
    ]
    # student 1 is shortlisted by all three companies -> guaranteed contention
    shortlists = {
        1: [1, 2, 3],
        2: [1, 2, 4],
        3: [1, 5, 6, 7],
    }
    room_ids = [1, 2]

    result, world = schedule_day(companies, shortlists, room_ids)

    # Reconstruct occupancy independently of the algorithm and assert no overlaps.
    seen_panel_slots = {}
    seen_room_slots = {}
    seen_student_slots = {}
    for iv in result.scheduled:
        dur = duration_to_slots(15)
        start = minute_to_slot(iv["start_min"])
        for s in range(start, start + dur):
            pk = (iv["panel_id"], s)
            rk = (iv["room_id"], s)
            sk = (iv["student_id"], s)
            assert pk not in seen_panel_slots, f"panel double-booked at slot {s}"
            assert rk not in seen_room_slots, f"room double-booked at slot {s}"
            assert sk not in seen_student_slots, f"student double-booked at slot {s}"
            seen_panel_slots[pk] = iv
            seen_room_slots[rk] = iv
            seen_student_slots[sk] = iv

    total_requested = sum(len(v) for v in shortlists.values())
    assert len(result.scheduled) + len(result.unscheduled) == total_requested
    # student 1 is triple-contended for a single-panel-each company with only
    # 4 fifteen-minute slots in the window -> not everyone can get all 3
    assert len(result.scheduled) > 0


def test_infeasible_reports_reason_not_silent_failure():
    """One panel, one 15-min slot window, three students all wanting it."""
    companies = [
        CompanyInput(id=1, day=1, window_start_min=540, window_end_min=555,
                     interview_duration_min=15, panel_ids=[101]),
    ]
    shortlists = {1: [1, 2, 3]}
    room_ids = [1]

    result, world = schedule_day(companies, shortlists, room_ids)

    assert len(result.scheduled) == 1
    assert len(result.unscheduled) == 2
    for u in result.unscheduled:
        assert u["reason"]  # never empty / silent


def test_room_scarcity_diagnosed_correctly():
    """Two companies, different panels, same tiny window, only one room."""
    companies = [
        CompanyInput(id=1, day=1, window_start_min=540, window_end_min=555,
                     interview_duration_min=15, panel_ids=[101]),
        CompanyInput(id=2, day=1, window_start_min=540, window_end_min=555,
                     interview_duration_min=15, panel_ids=[201]),
    ]
    shortlists = {1: [1], 2: [2]}
    room_ids = [1]  # only one room, one slot -> one of the two must fail

    result, world = schedule_day(companies, shortlists, room_ids)
    assert len(result.scheduled) == 1
    assert len(result.unscheduled) == 1
    assert "room" in result.unscheduled[0]["reason"]


def test_deterministic_given_same_input():
    companies = [
        CompanyInput(id=1, day=1, window_start_min=540, window_end_min=600,
                     interview_duration_min=15, panel_ids=[101, 102]),
    ]
    shortlists = {1: list(range(1, 9))}
    room_ids = [1, 2, 3]

    r1, _ = schedule_day(companies, shortlists, room_ids)
    r2, _ = schedule_day(companies, shortlists, room_ids)
    assert r1.scheduled == r2.scheduled
    assert r1.unscheduled == r2.unscheduled


def test_large_realistic_scale_runs_fast_and_stays_consistent():
    import random
    import time

    rng = random.Random(7)
    companies = []
    shortlists = {}
    panel_counter = 1000
    for cid in range(1, 21):  # 20 companies in one day
        num_panels = rng.randint(1, 5)
        panel_ids = list(range(panel_counter, panel_counter + num_panels))
        panel_counter += num_panels
        companies.append(CompanyInput(
            id=cid, day=1, window_start_min=540, window_end_min=1080,
            interview_duration_min=rng.choice([10, 15, 20, 30]),
            panel_ids=panel_ids,
        ))
        shortlists[cid] = rng.sample(range(1, 801), k=rng.randint(20, 250))

    room_ids = list(range(1, 21))

    start = time.time()
    result, world = schedule_day(companies, shortlists, room_ids)
    elapsed = time.time() - start

    total = sum(len(v) for v in shortlists.values())
    assert len(result.scheduled) + len(result.unscheduled) == total
    assert elapsed < 15, f"scheduling took too long: {elapsed:.2f}s"

    # spot-check: no student appears twice at overlapping slots
    by_student = {}
    for iv in result.scheduled:
        by_student.setdefault(iv["student_id"], []).append(iv)
    for sid, ivs in by_student.items():
        ivs_sorted = sorted(ivs, key=lambda x: x["start_min"])
        for a, b in zip(ivs_sorted, ivs_sorted[1:]):
            assert a["end_min"] <= b["start_min"], f"student {sid} double-booked"
