from sqlalchemy.orm import Session

from . import models
from .config import settings
from .core import generator
from .core.records import InterviewRecord
from .core.replanner import (
    replan_company_delay, replan_panel_drop, replan_room_unavailable,
    replan_student_withdraw,
)
from .core.scheduling_engine import CompanyInput, schedule_day


# --------------------------------------------------------------------------
# Dataset generation / seeding
# --------------------------------------------------------------------------
def reset_all(db: Session):
    db.query(models.Interview).delete()
    db.query(models.ReplanEvent).delete()
    db.query(models.RoomBlock).delete()
    db.query(models.Shortlist).delete()
    db.query(models.Panel).delete()
    db.query(models.Company).delete()
    db.query(models.Student).delete()
    db.query(models.Room).delete()
    db.commit()


def seed_database(db: Session, seed: int | None = None) -> dict:
    reset_all(db)
    gen_students, gen_companies, shortlist_idx_lists, room_names = generator.generate_dataset(seed)

    room_objs = [models.Room(name=n, capacity=1) for n in room_names]
    db.add_all(room_objs)

    student_objs = [
        models.Student(roll_no=s.roll_no, name=s.name, cgpa=s.cgpa, branch=s.branch)
        for s in gen_students
    ]
    db.add_all(student_objs)
    db.flush()  # assign ids

    company_objs = []
    for gc in gen_companies:
        company_objs.append(models.Company(
            name=gc.name, day=gc.day, priority_tier=gc.priority_tier,
            cgpa_cutoff=gc.cgpa_cutoff, interview_duration_min=gc.interview_duration_min,
            window_start_min=gc.window_start_min, window_end_min=gc.window_end_min,
            num_panels=gc.num_panels,
        ))
    db.add_all(company_objs)
    db.flush()

    panel_objs = []
    for c_obj, gc in zip(company_objs, gen_companies):
        for pn in range(1, gc.num_panels + 1):
            panel_objs.append(models.Panel(company_id=c_obj.id, panel_number=pn))
    db.add_all(panel_objs)
    db.flush()

    shortlist_objs = []
    for c_obj, student_idxs in zip(company_objs, shortlist_idx_lists):
        for s_idx in student_idxs:
            shortlist_objs.append(models.Shortlist(
                company_id=c_obj.id, student_id=student_objs[s_idx].id,
            ))
    db.add_all(shortlist_objs)
    db.commit()

    return {
        "students": len(student_objs), "companies": len(company_objs),
        "panels": len(panel_objs), "shortlists": len(shortlist_objs),
        "rooms": len(room_objs),
    }


# --------------------------------------------------------------------------
# Initial scheduling
# --------------------------------------------------------------------------
def run_initial_schedule(db: Session) -> dict:
    db.query(models.Interview).delete()
    db.commit()

    room_ids = [r.id for r in db.query(models.Room).all()]
    totals = {"scheduled": 0, "unscheduled": 0}

    for day in range(1, settings.NUM_DAYS + 1):
        companies = db.query(models.Company).filter(models.Company.day == day).all()
        if not companies:
            continue
        company_inputs = []
        shortlists = {}
        for c in companies:
            panel_ids = [p.id for p in c.panels if p.status == models.PanelStatus.ACTIVE]
            company_inputs.append(CompanyInput(
                id=c.id, day=c.day, window_start_min=c.window_start_min,
                window_end_min=c.window_end_min, interview_duration_min=c.interview_duration_min,
                panel_ids=panel_ids,
            ))
            student_ids = [sl.student_id for sl in c.shortlists]
            shortlists[c.id] = student_ids

        result, _world = schedule_day(company_inputs, shortlists, room_ids)

        interview_rows = []
        for s in result.scheduled:
            interview_rows.append(models.Interview(
                company_id=s["company_id"], student_id=s["student_id"], panel_id=s["panel_id"],
                room_id=s["room_id"], day=s["day"], start_min=s["start_min"], end_min=s["end_min"],
                status=models.InterviewStatus.SCHEDULED,
            ))
        for u in result.unscheduled:
            interview_rows.append(models.Interview(
                company_id=u["company_id"], student_id=u["student_id"], day=u["day"],
                status=models.InterviewStatus.UNSCHEDULED, unscheduled_reason=u["reason"],
            ))
        db.add_all(interview_rows)
        db.commit()
        totals["scheduled"] += len(result.scheduled)
        totals["unscheduled"] += len(result.unscheduled)

    return totals


# --------------------------------------------------------------------------
# Replan helpers: DB <-> InterviewRecord bridge
# --------------------------------------------------------------------------
def _load_day_records(db: Session, day: int) -> list[InterviewRecord]:
    rows = db.query(models.Interview).filter(models.Interview.day == day).all()
    return [
        InterviewRecord(
            id=r.id, company_id=r.company_id, student_id=r.student_id, panel_id=r.panel_id,
            room_id=r.room_id, day=r.day, start_min=r.start_min, end_min=r.end_min,
            status=r.status.value, unscheduled_reason=r.unscheduled_reason,
        )
        for r in rows
    ]


def _writeback(db: Session, records: list[InterviewRecord]):
    for rec in records:
        row = db.get(models.Interview, rec.id)
        row.company_id = rec.company_id
        row.student_id = rec.student_id
        row.panel_id = rec.panel_id
        row.room_id = rec.room_id
        row.day = rec.day
        row.start_min = rec.start_min
        row.end_min = rec.end_min
        row.status = models.InterviewStatus(rec.status)
        row.unscheduled_reason = rec.unscheduled_reason
    db.commit()


def _log_event(db: Session, event_type: str, payload: dict, diff: dict) -> models.ReplanEvent:
    ev = models.ReplanEvent(event_type=event_type, payload=payload, diff=diff)
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev


def _count_previously_scheduled(records: list[InterviewRecord]) -> int:
    return sum(1 for r in records if r.status == "scheduled")


def do_company_delay(db: Session, company_id: int, delay_min: int) -> dict:
    company = db.get(models.Company, company_id)
    if company is None:
        raise ValueError("company not found")
    day = company.day
    records = _load_day_records(db, day)
    before_scheduled = _count_previously_scheduled(records)
    panel_ids = [p.id for p in company.panels if p.status == models.PanelStatus.ACTIVE]
    room_ids = [r.id for r in db.query(models.Room).all()]

    old_start, old_end = company.window_start_min, company.window_end_min
    updated, diff = replan_company_delay(
        records, company_id=company_id, day=day,
        old_window_start_min=old_start, old_window_end_min=old_end,
        delay_min=delay_min, panel_ids=panel_ids, room_ids=room_ids,
    )
    _writeback(db, updated)

    company.delay_min = (company.delay_min or 0) + delay_min
    company.is_late = True
    company.window_start_min = min(old_start + delay_min, settings.DAY_END_MIN + settings.MAX_SPILLOVER_MIN)
    company.window_end_min = min(old_end + delay_min, settings.DAY_END_MIN + settings.MAX_SPILLOVER_MIN)
    db.commit()

    from .core.metrics import churn_pct
    diff_dict = diff.as_dict()
    diff_dict["churn_pct"] = churn_pct(len(diff.changes), before_scheduled)
    ev = _log_event(db, "company_delay", {"company_id": company_id, "delay_min": delay_min}, diff_dict)
    return {"event_id": ev.id, **diff_dict}


def do_panel_drop(db: Session, panel_id: int) -> dict:
    panel = db.get(models.Panel, panel_id)
    if panel is None:
        raise ValueError("panel not found")
    company = panel.company
    day = company.day
    records = _load_day_records(db, day)
    before_scheduled = _count_previously_scheduled(records)

    panel.status = models.PanelStatus.DROPPED
    db.commit()

    remaining_panel_ids = [p.id for p in company.panels if p.status == models.PanelStatus.ACTIVE]
    room_ids = [r.id for r in db.query(models.Room).all()]

    updated, diff = replan_panel_drop(
        records, dropped_panel_id=panel_id, company_id=company.id, day=day,
        remaining_panel_ids=remaining_panel_ids, room_ids=room_ids,
        window_start_min=company.window_start_min, window_end_min=company.window_end_min,
    )
    _writeback(db, updated)

    from .core.metrics import churn_pct
    diff_dict = diff.as_dict()
    diff_dict["churn_pct"] = churn_pct(len(diff.changes), before_scheduled)
    ev = _log_event(db, "panel_drop", {"panel_id": panel_id, "company_id": company.id}, diff_dict)
    return {"event_id": ev.id, **diff_dict}


def do_student_withdraw(db: Session, student_id: int, withdrawal_time_min: int | None, day: int) -> dict:
    student = db.get(models.Student, student_id)
    if student is None:
        raise ValueError("student not found")
    records = _load_day_records(db, day)
    before_scheduled = _count_previously_scheduled(records)

    company_duration = {c.id: c.interview_duration_min for c in db.query(models.Company).filter(models.Company.day == day).all()}

    updated, diff = replan_student_withdraw(
        records, student_id=student_id, day=day, withdrawal_time_min=withdrawal_time_min,
        company_duration_min=company_duration, allow_backfill=True,
    )
    _writeback(db, updated)

    student.withdrawn = True
    student.withdrawn_at_min = withdrawal_time_min
    db.commit()

    from .core.metrics import churn_pct
    diff_dict = diff.as_dict()
    diff_dict["churn_pct"] = churn_pct(len(diff.changes), before_scheduled)
    ev = _log_event(db, "student_withdraw", {"student_id": student_id, "withdrawal_time_min": withdrawal_time_min, "day": day}, diff_dict)
    return {"event_id": ev.id, **diff_dict}


def do_room_unavailable(db: Session, room_id: int, day: int, start_min: int, end_min: int, reason: str) -> dict:
    room = db.get(models.Room, room_id)
    if room is None:
        raise ValueError("room not found")
    records = _load_day_records(db, day)
    before_scheduled = _count_previously_scheduled(records)
    all_room_ids = [r.id for r in db.query(models.Room).all()]

    block = models.RoomBlock(room_id=room_id, day=day, start_min=start_min, end_min=end_min, reason=reason)
    db.add(block)
    db.commit()

    updated, diff = replan_room_unavailable(
        records, room_id=room_id, day=day, block_start_min=start_min, block_end_min=end_min,
        all_room_ids=all_room_ids,
    )
    _writeback(db, updated)

    from .core.metrics import churn_pct
    diff_dict = diff.as_dict()
    diff_dict["churn_pct"] = churn_pct(len(diff.changes), before_scheduled)
    ev = _log_event(db, "room_unavailable", {"room_id": room_id, "day": day, "start_min": start_min, "end_min": end_min, "reason": reason}, diff_dict)
    return {"event_id": ev.id, **diff_dict}
