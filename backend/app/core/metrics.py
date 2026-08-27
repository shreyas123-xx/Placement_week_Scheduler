"""
Metrics answer the brief's first defend-your-decisions question: what does
a 'good' schedule mean here? We report five numbers, each chosen because a
coordinator would actually act differently depending on its value:

  * completion_rate      -- the headline number: what fraction of required
                             interviews got a room+panel+time.
  * room_utilization      -- if this is low while completion is also low,
                             the bottleneck is panels/student-time, not
                             rooms, and buying more rooms won't help.
  * panel_utilization     -- per company; a company sitting at 40% panel
                             utilization with unscheduled students usually
                             means its shortlist is badly time-boxed, not
                             genuinely infeasible.
  * avg_student_wait_min  -- average idle time between a student's
                             consecutive interviews on the same day; a
                             schedule can hit 100% completion and still be
                             bad for people if it makes them sit around.
  * replan_churn_pct      -- (used per replan event) how much of the
                             previously-settled schedule a disruption's fix
                             touched. This is the number that tells the
                             coordinator whether a proposed replan is safe
                             to auto-apply or needs a human look first.
"""
from collections import defaultdict

from sqlalchemy.orm import Session

from .. import models


def completion_rate(db: Session, day: int | None = None) -> dict:
    q = db.query(models.Interview)
    if day is not None:
        q = q.filter(models.Interview.day == day)
    rows = q.all()
    total = len(rows)
    scheduled = sum(1 for r in rows if r.status == models.InterviewStatus.SCHEDULED)
    cancelled = sum(1 for r in rows if r.status == models.InterviewStatus.CANCELLED)
    unscheduled = sum(1 for r in rows if r.status == models.InterviewStatus.UNSCHEDULED)
    pct = round(scheduled / total * 100, 1) if total else 0.0
    return {
        "total_required": total, "scheduled": scheduled,
        "unscheduled": unscheduled, "cancelled": cancelled,
        "completion_rate_pct": pct,
    }


def completion_by_company(db: Session) -> list[dict]:
    companies = db.query(models.Company).all()
    out = []
    for c in companies:
        rows = db.query(models.Interview).filter(models.Interview.company_id == c.id).all()
        total = len(rows)
        scheduled = sum(1 for r in rows if r.status == models.InterviewStatus.SCHEDULED)
        unscheduled = sum(1 for r in rows if r.status == models.InterviewStatus.UNSCHEDULED)
        out.append({
            "company_id": c.id, "company_name": c.name, "day": c.day,
            "tier": c.priority_tier.value, "total": total, "scheduled": scheduled,
            "unscheduled": unscheduled,
            "completion_rate_pct": round(scheduled / total * 100, 1) if total else 0.0,
        })
    return sorted(out, key=lambda x: x["completion_rate_pct"])


def room_utilization(db: Session, day: int) -> dict:
    from ..config import settings
    rooms = db.query(models.Room).count()
    window_min = settings.DAY_END_MIN - settings.DAY_START_MIN
    total_capacity_min = rooms * window_min
    booked = db.query(models.Interview).filter(
        models.Interview.day == day, models.Interview.status == models.InterviewStatus.SCHEDULED,
    ).all()
    booked_min = sum((r.end_min - r.start_min) for r in booked)
    pct = round(booked_min / total_capacity_min * 100, 1) if total_capacity_min else 0.0
    return {"day": day, "rooms": rooms, "booked_minutes": booked_min,
            "capacity_minutes": total_capacity_min, "utilization_pct": pct}


def panel_utilization_by_company(db: Session, day: int) -> list[dict]:
    companies = db.query(models.Company).filter(models.Company.day == day).all()
    out = []
    for c in companies:
        num_active_panels = db.query(models.Panel).filter(
            models.Panel.company_id == c.id, models.Panel.status == models.PanelStatus.ACTIVE,
        ).count()
        window_min = c.window_end_min - c.window_start_min
        capacity_min = num_active_panels * window_min
        booked = db.query(models.Interview).filter(
            models.Interview.company_id == c.id, models.Interview.status == models.InterviewStatus.SCHEDULED,
        ).all()
        booked_min = sum((r.end_min - r.start_min) for r in booked)
        pct = round(booked_min / capacity_min * 100, 1) if capacity_min else 0.0
        out.append({
            "company_id": c.id, "company_name": c.name, "active_panels": num_active_panels,
            "utilization_pct": pct,
        })
    return sorted(out, key=lambda x: x["utilization_pct"])


def avg_student_wait_minutes(db: Session, day: int) -> dict:
    rows = db.query(models.Interview).filter(
        models.Interview.day == day, models.Interview.status == models.InterviewStatus.SCHEDULED,
    ).all()
    by_student = defaultdict(list)
    for r in rows:
        by_student[r.student_id].append((r.start_min, r.end_min))

    total_wait = 0
    students_with_gaps = 0
    for sid, spans in by_student.items():
        if len(spans) < 2:
            continue
        spans.sort()
        gap_sum = 0
        for a, b in zip(spans, spans[1:]):
            gap = max(0, b[0] - a[1])
            gap_sum += gap
        total_wait += gap_sum
        students_with_gaps += 1

    avg = round(total_wait / students_with_gaps, 1) if students_with_gaps else 0.0
    return {"day": day, "students_with_multiple_interviews": students_with_gaps,
            "avg_wait_minutes": avg}


def churn_pct(changes_count: int, total_scheduled_before: int) -> float:
    if total_scheduled_before == 0:
        return 0.0
    return round(changes_count / total_scheduled_before * 100, 2)


def full_summary(db: Session) -> dict:
    from ..config import settings
    overall = completion_rate(db)
    per_day = []
    for day in range(1, settings.NUM_DAYS + 1):
        per_day.append({
            "day": day,
            "completion": completion_rate(db, day=day),
            "room_utilization": room_utilization(db, day=day),
            "student_wait": avg_student_wait_minutes(db, day=day),
        })
    return {
        "overall": overall,
        "by_day": per_day,
        "by_company": completion_by_company(db),
    }
