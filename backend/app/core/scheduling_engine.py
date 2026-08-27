"""
The initial-schedule algorithm.

This is a deliberately *heuristic* scheduler, not an exact CSP/ILP solver —
worth defending explicitly since it's the central design decision of the
assignment:

  * At this scale (thousands of interviews, tens of thousands of
    student/panel/room slot combinations) an exact solver is not what a
    real coordinator needs on placement day anyway — they need an answer
    in milliseconds when a company walks in 3 hours late, not a
    re-optimisation that takes minutes and reshuffles everyone.
  * A greedy, priority-ordered, first-fit heuristic is fast, deterministic,
    and — crucially — *local*: the same booking primitives (SchedulingWorld)
    are reused by the replanner, so "replan with minimal disturbance" falls
    out naturally instead of needing a separate diffing algorithm bolted
    onto an optimiser's output.
  * We trade a small amount of optimality (a perfect solver might squeeze
    out a few more percent scheduled) for speed and, more importantly,
    predictability: the coordinator can understand *why* a given interview
    didn't get a slot, because the algorithm's decisions are legible
    (see `diagnose_unscheduled`), which an ILP's dual values are not.

Ordering choices (see README for the full defence):
  1. Companies are scheduled most-oversubscribed-first: companies whose
     shortlist most exceeds their own panel capacity go first, so they get
     first claim on shared students' free slots. Scheduling the roomiest
     companies first would let them "steal" slots from tightly-constrained
     ones purely by going first.
  2. Within a company, the most-contested students (shortlisted by the
     most *other* companies on the same day) are scheduled first, since
     they are the ones most likely to run out of common free time.
"""
from dataclasses import dataclass, field

from .timeutil import duration_to_slots, minute_to_slot
from .world import SchedulingWorld


@dataclass
class CompanyInput:
    id: int
    day: int
    window_start_min: int
    window_end_min: int
    interview_duration_min: int
    panel_ids: list


@dataclass
class ScheduleResult:
    scheduled: list = field(default_factory=list)     # dicts: company_id, student_id, panel_id, room_id, day, start_min, end_min
    unscheduled: list = field(default_factory=list)    # dicts: company_id, student_id, reason


def _company_order(companies: list[CompanyInput], shortlists: dict[int, list[int]]):
    def oversubscription(c: CompanyInput):
        window_slots = duration_to_slots(c.window_end_min - c.window_start_min)
        dur_slots = duration_to_slots(c.interview_duration_min)
        capacity = max(1, len(c.panel_ids) * (window_slots // max(dur_slots, 1)))
        demand = len(shortlists.get(c.id, []))
        return demand / capacity

    return sorted(companies, key=oversubscription, reverse=True)


def _student_order_for_company(company_id, student_ids, contest_count: dict):
    return sorted(student_ids, key=lambda sid: contest_count.get(sid, 0), reverse=True)


def _diagnose(world: SchedulingWorld, student_id, panel_ids, room_ids, dur_slots, earliest, latest_excl) -> str:
    """Best-effort explanation for why a slot search failed."""
    any_panel_free = False
    any_panel_free_and_student_free = False
    for start in range(earliest, latest_excl - dur_slots + 1):
        panel_ok = any(world.panel_free(p, start, dur_slots) for p in panel_ids)
        if panel_ok:
            any_panel_free = True
            if world.student_free(student_id, start, dur_slots):
                any_panel_free_and_student_free = True
                break
    if not any_panel_free:
        return "company's panels are fully booked in their allotted window"
    if not any_panel_free_and_student_free:
        return "student has clashing interviews with other companies at every mutual free slot"
    return "panel and student were both free at some point, but no room was free at the same time"


def schedule_day(
    companies: list[CompanyInput],
    shortlists: dict[int, list[int]],
    room_ids: list[int],
    world: SchedulingWorld | None = None,
) -> tuple[ScheduleResult, SchedulingWorld]:
    """Schedules every shortlisted (company, student) pair for one day."""
    if world is None:
        world = SchedulingWorld(day=companies[0].day if companies else 0)

    result = ScheduleResult()

    # how many *other* companies (same day) also want this student
    contest_count: dict[int, int] = {}
    for cid, students in shortlists.items():
        for sid in students:
            contest_count[sid] = contest_count.get(sid, 0) + 1

    for company in _company_order(companies, shortlists):
        dur_slots = duration_to_slots(company.interview_duration_min)
        earliest = minute_to_slot(company.window_start_min)
        latest_excl = minute_to_slot(company.window_end_min)
        students = _student_order_for_company(company.id, shortlists.get(company.id, []), contest_count)

        for student_id in students:
            found = world.find_slot(
                student_id=student_id,
                panel_ids=company.panel_ids,
                room_ids=room_ids,
                dur_slots=dur_slots,
                earliest_slot=earliest,
                latest_slot_exclusive=latest_excl,
            )
            if found is None:
                reason = _diagnose(world, student_id, company.panel_ids, room_ids, dur_slots, earliest, latest_excl)
                result.unscheduled.append({
                    "company_id": company.id, "student_id": student_id, "reason": reason,
                    "day": company.day,
                })
                continue

            panel_id, room_id, start_slot = found
            world.book(student_id, panel_id, room_id, start_slot, dur_slots)
            from .timeutil import slot_to_minute
            start_min = slot_to_minute(start_slot)
            result.scheduled.append({
                "company_id": company.id, "student_id": student_id,
                "panel_id": panel_id, "room_id": room_id, "day": company.day,
                "start_min": start_min, "end_min": start_min + company.interview_duration_min,
            })

    return result, world
