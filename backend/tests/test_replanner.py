import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.records import InterviewRecord
from app.core.replanner import (
    replan_company_delay, replan_panel_drop, replan_student_withdraw,
    replan_room_unavailable,
)
from app.core.timeutil import minute_to_slot


def mk(id, company_id, student_id, panel_id, room_id, day, start_min, end_min, status="scheduled"):
    return InterviewRecord(
        id=id, company_id=company_id, student_id=student_id, panel_id=panel_id,
        room_id=room_id, day=day, start_min=start_min, end_min=end_min, status=status,
    )


def assert_no_overlaps(interviews):
    scheduled = [iv for iv in interviews if iv.status == "scheduled"]
    by_panel, by_room, by_student = {}, {}, {}
    for iv in scheduled:
        for bucket, key in ((by_panel, iv.panel_id), (by_room, iv.room_id), (by_student, iv.student_id)):
            bucket.setdefault(key, []).append((iv.start_min, iv.end_min, iv.id))
    for bucket in (by_panel, by_room, by_student):
        for key, spans in bucket.items():
            spans.sort()
            for a, b in zip(spans, spans[1:]):
                assert a[1] <= b[0], f"overlap for key={key}: {a} vs {b}"


# --------------------------------------------------------------------------
# Company delay
# --------------------------------------------------------------------------
def test_company_delay_only_moves_conflicting_interviews():
    # Company 1 runs 9:00-10:00 (540-600) with panel 101, 15-min interviews.
    interviews = [
        mk(1, 1, student_id=1, panel_id=101, room_id=1, day=1, start_min=540, end_min=555),
        mk(2, 1, student_id=2, panel_id=101, room_id=1, day=1, start_min=555, end_min=570),
        mk(3, 1, student_id=3, panel_id=101, room_id=1, day=1, start_min=570, end_min=585),
        mk(4, 1, student_id=4, panel_id=101, room_id=1, day=1, start_min=585, end_min=600),
    ]
    # Delay by 30 minutes -> new window starts at 570. Interviews 1 & 2 (before 570) must move.
    updated, diff = replan_company_delay(
        interviews, company_id=1, day=1, old_window_start_min=540, old_window_end_min=600,
        delay_min=30, panel_ids=[101], room_ids=[1, 2],
    )
    assert_no_overlaps(updated)
    moved_ids = {c.interview_id for c in diff.changes if c.change_type == "moved"}
    # interviews 3 and 4 already start at/after 570 -> untouched
    assert 3 not in moved_ids
    assert 4 not in moved_ids
    # interviews 1 and 2 needed to move
    assert {1, 2} <= moved_ids or any(c.change_type == "newly_unscheduled" for c in diff.changes)
    # nothing after the delay window got touched
    iv3 = next(iv for iv in updated if iv.id == 3)
    iv4 = next(iv for iv in updated if iv.id == 4)
    assert iv3.start_min == 570
    assert iv4.start_min == 585


def test_company_delay_reports_unscheduled_when_no_room_left():
    # Extremely tight: 1 panel, 1 room, no spare capacity anywhere to push into.
    interviews = [
        mk(1, 1, student_id=1, panel_id=101, room_id=1, day=1, start_min=540, end_min=555),
    ]
    updated, diff = replan_company_delay(
        interviews, company_id=1, day=1, old_window_start_min=540, old_window_end_min=555,
        delay_min=99999,  # push it past the spillover grace window entirely
        panel_ids=[101], room_ids=[1],
    )
    iv = updated[0]
    assert iv.status == "unscheduled"
    assert iv.unscheduled_reason
    assert diff.changes[0].change_type == "newly_unscheduled"


# --------------------------------------------------------------------------
# Panel drop
# --------------------------------------------------------------------------
def test_panel_drop_prefers_same_slot_different_panel():
    interviews = [
        mk(1, 1, student_id=1, panel_id=101, room_id=1, day=1, start_min=540, end_min=555),
        # panel 102 is free at the same slot
    ]
    updated, diff = replan_panel_drop(
        interviews, dropped_panel_id=101, company_id=1, day=1,
        remaining_panel_ids=[102], room_ids=[1, 2],
        window_start_min=540, window_end_min=600,
    )
    iv = updated[0]
    assert iv.status == "scheduled"
    assert iv.panel_id == 102
    assert iv.start_min == 540  # unchanged — minimal disturbance
    assert iv.room_id == 1      # unchanged
    assert diff.changes[0].change_type == "moved"


def test_panel_drop_with_no_remaining_panels_is_unscheduled_not_silent():
    interviews = [
        mk(1, 1, student_id=1, panel_id=101, room_id=1, day=1, start_min=540, end_min=555),
    ]
    updated, diff = replan_panel_drop(
        interviews, dropped_panel_id=101, company_id=1, day=1,
        remaining_panel_ids=[], room_ids=[1, 2],
        window_start_min=540, window_end_min=600,
    )
    assert updated[0].status == "unscheduled"
    assert updated[0].unscheduled_reason
    assert_no_overlaps(updated)


def test_panel_drop_does_not_touch_other_companies_interviews():
    interviews = [
        mk(1, 1, student_id=1, panel_id=101, room_id=1, day=1, start_min=540, end_min=555),
        mk(2, 2, student_id=2, panel_id=201, room_id=2, day=1, start_min=540, end_min=555),
    ]
    updated, diff = replan_panel_drop(
        interviews, dropped_panel_id=101, company_id=1, day=1,
        remaining_panel_ids=[103], room_ids=[1, 2, 3],
        window_start_min=540, window_end_min=600,
    )
    other = next(iv for iv in updated if iv.id == 2)
    assert other.panel_id == 201 and other.start_min == 540  # completely untouched
    assert len(diff.changes) == 1  # only the affected interview shows up in the diff


# --------------------------------------------------------------------------
# Student withdrawal
# --------------------------------------------------------------------------
def test_student_withdraw_cancels_only_future_interviews():
    interviews = [
        mk(1, 1, student_id=1, panel_id=101, room_id=1, day=1, start_min=540, end_min=555),  # past
        mk(2, 2, student_id=1, panel_id=201, room_id=2, day=1, start_min=700, end_min=715),  # future
    ]
    updated, diff = replan_student_withdraw(
        interviews, student_id=1, day=1, withdrawal_time_min=600,
        company_duration_min={1: 15, 2: 15}, allow_backfill=False,
    )
    past = next(iv for iv in updated if iv.id == 1)
    future = next(iv for iv in updated if iv.id == 2)
    assert past.status == "scheduled"   # already happened, untouched
    assert future.status == "cancelled"


def test_student_withdraw_backfills_freed_slot():
    interviews = [
        mk(1, 1, student_id=1, panel_id=101, room_id=1, day=1, start_min=540, end_min=555),
        mk(2, 1, student_id=2, panel_id=None, room_id=None, day=1, start_min=None, end_min=None, status="unscheduled"),
    ]
    updated, diff = replan_student_withdraw(
        interviews, student_id=1, day=1, withdrawal_time_min=None,
        company_duration_min={1: 15}, allow_backfill=True,
    )
    backfilled = next(iv for iv in updated if iv.id == 2)
    assert backfilled.status == "scheduled"
    assert backfilled.panel_id == 101
    assert backfilled.room_id == 1
    assert backfilled.start_min == 540
    assert backfilled.end_min == 555
    kinds = {c.change_type for c in diff.changes}
    assert "cancelled" in kinds and "backfilled" in kinds
    assert_no_overlaps(updated)


# --------------------------------------------------------------------------
# Room unavailable
# --------------------------------------------------------------------------
def test_room_unavailable_moves_only_overlapping_interviews_to_other_room():
    interviews = [
        mk(1, 1, student_id=1, panel_id=101, room_id=5, day=1, start_min=540, end_min=555),
        mk(2, 1, student_id=2, panel_id=102, room_id=5, day=1, start_min=700, end_min=715),  # outside block window
    ]
    updated, diff = replan_room_unavailable(
        interviews, room_id=5, day=1, block_start_min=540, block_end_min=600,
        all_room_ids=[5, 6, 7],
    )
    iv1 = next(iv for iv in updated if iv.id == 1)
    iv2 = next(iv for iv in updated if iv.id == 2)
    assert iv1.room_id != 5 and iv1.status == "scheduled"
    assert iv1.start_min == 540  # same-slot repair, only room changes
    assert iv2.room_id == 5      # untouched, outside the blocked window
    assert_no_overlaps(updated)


def test_room_unavailable_reports_unscheduled_if_truly_no_room():
    interviews = [
        mk(1, 1, student_id=1, panel_id=101, room_id=5, day=1, start_min=540, end_min=555),
    ]
    updated, diff = replan_room_unavailable(
        interviews, room_id=5, day=1, block_start_min=0, block_end_min=100000,
        all_room_ids=[5],  # no alternate room exists at all
    )
    assert updated[0].status == "unscheduled"
    assert updated[0].unscheduled_reason
