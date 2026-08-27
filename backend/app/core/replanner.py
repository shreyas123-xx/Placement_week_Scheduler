"""
Minimal-disturbance replanning.

The brief's own warning is the design spec here: "Moving 200 appointments
to fix a 2-hour delay is technically valid and practically a disaster."
So every repair function below follows the same discipline:

  1. Touch only the interviews that are *actually* invalidated by the
     disruption (wrong room, dropped panel, delayed company, withdrawn
     student) — never the whole day's schedule.
  2. When an interview must move, prefer the smallest possible change
     first: same time slot with a different panel/room before a
     different time slot; only fall back to a wider search if that
     fails.
  3. Preserve relative order: when several interviews of the same
     student/company must move, they are re-placed in their original
     chronological order, so a student's afternoon doesn't get
     reordered for no reason.
  4. Never fail silently. Anything that can't be repaired is reported as
     newly_unscheduled with a reason, exactly like the initial pass.

Every repair returns a `Diff`: the full before/after for every interview
it touched, plus the set of students and companies who need to be told.
That diff is the artifact the coordinator's dashboard is built around.
"""
from dataclasses import dataclass, field

from .records import InterviewRecord
from .timeutil import (
    DAY_END_WITH_SPILLOVER, duration_to_slots, minute_to_slot, slot_to_minute,
)
from .world import SchedulingWorld


@dataclass
class ChangeEntry:
    interview_id: int
    student_id: int
    company_id: int
    change_type: str  # "moved" | "cancelled" | "newly_unscheduled" | "backfilled"
    before: dict
    after: dict


@dataclass
class Diff:
    changes: list = field(default_factory=list)
    reason_summary: str = ""

    @property
    def affected_students(self):
        return sorted({c.student_id for c in self.changes})

    @property
    def affected_companies(self):
        return sorted({c.company_id for c in self.changes})

    def as_dict(self):
        return {
            "reason_summary": self.reason_summary,
            "changes": [
                {
                    "interview_id": c.interview_id, "student_id": c.student_id,
                    "company_id": c.company_id, "change_type": c.change_type,
                    "before": c.before, "after": c.after,
                }
                for c in self.changes
            ],
            "affected_students": self.affected_students,
            "affected_companies": self.affected_companies,
            "counts": _tally([c.change_type for c in self.changes]),
        }


def _tally(kinds):
    out = {}
    for k in kinds:
        out[k] = out.get(k, 0) + 1
    return out


def _snapshot(iv: InterviewRecord) -> dict:
    return {
        "day": iv.day, "start_min": iv.start_min, "end_min": iv.end_min,
        "room_id": iv.room_id, "panel_id": iv.panel_id, "status": iv.status,
    }


def build_world(
    interviews: list[InterviewRecord], day: int, exclude_ids: set | None = None
) -> SchedulingWorld:
    exclude_ids = exclude_ids or set()
    world = SchedulingWorld(day=day)
    for iv in interviews:
        if iv.status != "scheduled" or iv.day != day or iv.id in exclude_ids:
            continue
        dur = duration_to_slots(iv.end_min - iv.start_min)
        start_slot = minute_to_slot(iv.start_min)
        world.book(iv.student_id, iv.panel_id, iv.room_id, start_slot, dur)
    return world


# --------------------------------------------------------------------------
# 1. Company arrives N minutes late
# --------------------------------------------------------------------------
def replan_company_delay(
    interviews: list[InterviewRecord],
    company_id: int,
    day: int,
    old_window_start_min: int,
    old_window_end_min: int,
    delay_min: int,
    panel_ids: list,
    room_ids: list,
) -> tuple[list[InterviewRecord], Diff]:
    new_start = old_window_start_min + delay_min
    new_end = min(old_window_end_min + delay_min, DAY_END_WITH_SPILLOVER)

    company_ivs = [iv for iv in interviews if iv.company_id == company_id and iv.day == day]
    affected = sorted(
        (iv for iv in company_ivs if iv.status == "scheduled" and iv.start_min < new_start),
        key=lambda iv: iv.start_min,
    )
    affected_ids = {iv.id for iv in affected}

    world = build_world(interviews, day, exclude_ids=affected_ids)
    diff = Diff(reason_summary=f"Company {company_id} delayed {delay_min} min on day {day}")

    for iv in affected:
        before = _snapshot(iv)
        dur = duration_to_slots(iv.end_min - iv.start_min)
        found = world.find_slot(
            iv.student_id, [iv.panel_id] + [p for p in panel_ids if p != iv.panel_id],
            room_ids, dur, minute_to_slot(new_start), minute_to_slot(new_end),
        )
        if found is None:
            iv.status = "unscheduled"
            iv.unscheduled_reason = "delay left no available slot before day-end/grace window"
            iv.panel_id, iv.room_id, iv.start_min, iv.end_min = None, None, None, None
            diff.changes.append(ChangeEntry(
                iv.id, iv.student_id, iv.company_id, "newly_unscheduled", before, _snapshot(iv),
            ))
            continue
        panel_id, room_id, start_slot = found
        world.book(iv.student_id, panel_id, room_id, start_slot, dur)
        iv.panel_id, iv.room_id = panel_id, room_id
        iv.start_min = slot_to_minute(start_slot)
        iv.end_min = iv.start_min + (before["end_min"] - before["start_min"])
        diff.changes.append(ChangeEntry(
            iv.id, iv.student_id, iv.company_id, "moved", before, _snapshot(iv),
        ))

    return interviews, diff


# --------------------------------------------------------------------------
# 2. A panel drops out
# --------------------------------------------------------------------------
def replan_panel_drop(
    interviews: list[InterviewRecord],
    dropped_panel_id: int,
    company_id: int,
    day: int,
    remaining_panel_ids: list,
    room_ids: list,
    window_start_min: int,
    window_end_min: int,
) -> tuple[list[InterviewRecord], Diff]:
    affected = sorted(
        (iv for iv in interviews
         if iv.panel_id == dropped_panel_id and iv.status == "scheduled" and iv.day == day),
        key=lambda iv: iv.start_min,
    )
    affected_ids = {iv.id for iv in affected}
    world = build_world(interviews, day, exclude_ids=affected_ids)
    diff = Diff(reason_summary=f"Panel {dropped_panel_id} dropped (company {company_id}, day {day})")

    if not remaining_panel_ids:
        for iv in affected:
            before = _snapshot(iv)
            iv.status = "unscheduled"
            iv.unscheduled_reason = "company has no remaining panels after the drop"
            iv.panel_id, iv.room_id, iv.start_min, iv.end_min = None, None, None, None
            diff.changes.append(ChangeEntry(iv.id, iv.student_id, iv.company_id, "newly_unscheduled", before, _snapshot(iv)))
        return interviews, diff

    for iv in affected:
        before = _snapshot(iv)
        dur = duration_to_slots(before["end_min"] - before["start_min"])
        same_slot = minute_to_slot(before["start_min"])

        # Prefer: same time slot, same room, a different panel (zero time
        # change — the smallest repair possible for this kind of disruption).
        found = None
        for panel_id in remaining_panel_ids:
            if world.panel_free(panel_id, same_slot, dur) and world.room_free(before["room_id"], same_slot, dur):
                found = (panel_id, before["room_id"], same_slot)
                break
        if found is None:
            found = world.find_slot(
                iv.student_id, remaining_panel_ids, room_ids, dur,
                minute_to_slot(window_start_min), minute_to_slot(window_end_min),
            )

        if found is None:
            iv.status = "unscheduled"
            iv.unscheduled_reason = "no remaining panel had a free slot after the drop"
            iv.panel_id, iv.room_id, iv.start_min, iv.end_min = None, None, None, None
            diff.changes.append(ChangeEntry(iv.id, iv.student_id, iv.company_id, "newly_unscheduled", before, _snapshot(iv)))
            continue

        panel_id, room_id, start_slot = found
        world.book(iv.student_id, panel_id, room_id, start_slot, dur)
        iv.panel_id, iv.room_id = panel_id, room_id
        iv.start_min = slot_to_minute(start_slot)
        iv.end_min = iv.start_min + (before["end_min"] - before["start_min"])
        diff.changes.append(ChangeEntry(iv.id, iv.student_id, iv.company_id, "moved", before, _snapshot(iv)))

    return interviews, diff


# --------------------------------------------------------------------------
# 3. A student withdraws (optionally with backfill of the freed slots)
# --------------------------------------------------------------------------
def replan_student_withdraw(
    interviews: list[InterviewRecord],
    student_id: int,
    day: int,
    withdrawal_time_min: int | None,
    company_duration_min: dict,
    allow_backfill: bool = True,
) -> tuple[list[InterviewRecord], Diff]:
    diff = Diff(reason_summary=f"Student {student_id} withdrew on day {day}"
                                + (f" at {withdrawal_time_min} min" if withdrawal_time_min else ""))

    freed_slots = []  # (company_id, panel_id, room_id, start_slot, dur_slots, window info not needed)
    for iv in interviews:
        if iv.student_id != student_id or iv.status != "scheduled" or iv.day != day:
            continue
        if withdrawal_time_min is not None and iv.start_min < withdrawal_time_min:
            continue  # interview already happened before the withdrawal
        before = _snapshot(iv)
        dur = duration_to_slots(iv.end_min - iv.start_min)
        freed_slots.append((iv.company_id, iv.panel_id, iv.room_id, minute_to_slot(iv.start_min), dur))
        iv.status = "cancelled"
        iv.unscheduled_reason = None
        old_panel, old_room = iv.panel_id, iv.room_id
        iv.panel_id, iv.room_id, iv.start_min, iv.end_min = None, None, None, None
        diff.changes.append(ChangeEntry(iv.id, iv.student_id, iv.company_id, "cancelled", before, _snapshot(iv)))

    if not allow_backfill or not freed_slots:
        return interviews, diff

    world = build_world(interviews, day)
    # candidates: currently-unscheduled interview rows for the same companies
    candidates_by_company: dict[int, list[InterviewRecord]] = {}
    for iv in interviews:
        if iv.status == "unscheduled" and iv.day == day:
            candidates_by_company.setdefault(iv.company_id, []).append(iv)

    for company_id, panel_id, room_id, start_slot, dur in freed_slots:
        pool = candidates_by_company.get(company_id, [])
        duration_min = company_duration_min.get(company_id)
        if duration_min is None:
            continue
        for cand in pool:
            if world.is_free(cand.student_id, panel_id, room_id, start_slot, dur):
                before = _snapshot(cand)
                world.book(cand.student_id, panel_id, room_id, start_slot, dur)
                cand.status = "scheduled"
                cand.unscheduled_reason = None
                cand.panel_id, cand.room_id = panel_id, room_id
                cand.start_min = slot_to_minute(start_slot)
                cand.end_min = cand.start_min + duration_min
                diff.changes.append(ChangeEntry(cand.id, cand.student_id, cand.company_id, "backfilled", before, _snapshot(cand)))
                pool.remove(cand)
                break

    return interviews, diff


# --------------------------------------------------------------------------
# 4. A room becomes unavailable
# --------------------------------------------------------------------------
def replan_room_unavailable(
    interviews: list[InterviewRecord],
    room_id: int,
    day: int,
    block_start_min: int,
    block_end_min: int,
    all_room_ids: list,
) -> tuple[list[InterviewRecord], Diff]:
    affected = sorted(
        (iv for iv in interviews
         if iv.room_id == room_id and iv.status == "scheduled" and iv.day == day
         and iv.start_min < block_end_min and iv.end_min > block_start_min),
        key=lambda iv: iv.start_min,
    )
    affected_ids = {iv.id for iv in affected}
    world = build_world(interviews, day, exclude_ids=affected_ids)
    world.block_room(room_id, minute_to_slot(block_start_min), duration_to_slots(block_end_min - block_start_min))
    diff = Diff(reason_summary=f"Room {room_id} unavailable {block_start_min}-{block_end_min} on day {day}")

    other_rooms = [r for r in all_room_ids if r != room_id]

    for iv in affected:
        before = _snapshot(iv)
        dur = duration_to_slots(before["end_min"] - before["start_min"])
        same_slot = minute_to_slot(before["start_min"])

        found = None
        for alt_room in other_rooms:
            if world.room_free(alt_room, same_slot, dur):
                found = (iv.panel_id, alt_room, same_slot)
                break
        if found is None:
            # widen search but keep the same panel (panel isn't the problem)
            found = world.find_slot(
                iv.student_id, [iv.panel_id], other_rooms, dur,
                same_slot, same_slot + duration_to_slots(240),  # search up to 4h forward
            )

        if found is None:
            iv.status = "unscheduled"
            iv.unscheduled_reason = "no alternate room available for the blocked window"
            iv.panel_id, iv.room_id, iv.start_min, iv.end_min = None, None, None, None
            diff.changes.append(ChangeEntry(iv.id, iv.student_id, iv.company_id, "newly_unscheduled", before, _snapshot(iv)))
            continue

        panel_id, room_id_new, start_slot = found
        world.book(iv.student_id, panel_id, room_id_new, start_slot, dur)
        iv.panel_id, iv.room_id = panel_id, room_id_new
        iv.start_min = slot_to_minute(start_slot)
        iv.end_min = iv.start_min + (before["end_min"] - before["start_min"])
        diff.changes.append(ChangeEntry(iv.id, iv.student_id, iv.company_id, "moved", before, _snapshot(iv)))

    return interviews, diff
