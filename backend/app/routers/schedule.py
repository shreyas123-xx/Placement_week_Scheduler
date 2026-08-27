from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from .. import models
from ..core.timeutil import fmt_minute
from ..database import get_db

router = APIRouter(prefix="/api/schedule", tags=["schedule"])


def _serialize(iv: models.Interview) -> dict:
    return {
        "id": iv.id,
        "company_id": iv.company_id,
        "company_name": iv.company.name if iv.company else None,
        "student_id": iv.student_id,
        "student_name": iv.student.name if iv.student else None,
        "student_roll_no": iv.student.roll_no if iv.student else None,
        "panel_id": iv.panel_id,
        "panel_number": iv.panel.panel_number if iv.panel else None,
        "room_id": iv.room_id,
        "room_name": iv.room.name if iv.room else None,
        "day": iv.day,
        "start_min": iv.start_min,
        "end_min": iv.end_min,
        "start_time": fmt_minute(iv.start_min) if iv.start_min is not None else None,
        "end_time": fmt_minute(iv.end_min) if iv.end_min is not None else None,
        "status": iv.status.value,
        "unscheduled_reason": iv.unscheduled_reason,
    }


@router.get("")
def list_interviews(
    day: Optional[int] = None,
    company_id: Optional[int] = None,
    student_id: Optional[int] = None,
    room_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 500,
    db: Session = Depends(get_db),
):
    q = db.query(models.Interview).options(
        joinedload(models.Interview.company),
        joinedload(models.Interview.student),
        joinedload(models.Interview.panel),
        joinedload(models.Interview.room),
    )
    if day is not None:
        q = q.filter(models.Interview.day == day)
    if company_id is not None:
        q = q.filter(models.Interview.company_id == company_id)
    if student_id is not None:
        q = q.filter(models.Interview.student_id == student_id)
    if room_id is not None:
        q = q.filter(models.Interview.room_id == room_id)
    if status is not None:
        q = q.filter(models.Interview.status == models.InterviewStatus(status))
    q = q.order_by(models.Interview.day, models.Interview.start_min)
    rows = q.limit(limit).all()
    return [_serialize(r) for r in rows]


@router.get("/unscheduled")
def unscheduled_report(day: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(models.Interview).options(
        joinedload(models.Interview.company), joinedload(models.Interview.student),
    ).filter(models.Interview.status == models.InterviewStatus.UNSCHEDULED)
    if day is not None:
        q = q.filter(models.Interview.day == day)
    rows = q.all()

    grouped: dict[int, dict] = {}
    for r in rows:
        g = grouped.setdefault(r.company_id, {
            "company_id": r.company_id, "company_name": r.company.name if r.company else None,
            "day": r.day, "count": 0, "reasons": {}, "students": [],
        })
        g["count"] += 1
        g["reasons"][r.unscheduled_reason] = g["reasons"].get(r.unscheduled_reason, 0) + 1
        g["students"].append({"student_id": r.student_id, "student_name": r.student.name if r.student else None, "reason": r.unscheduled_reason})

    return sorted(grouped.values(), key=lambda x: -x["count"])


@router.get("/student/{student_id}")
def student_schedule(student_id: int, db: Session = Depends(get_db)):
    rows = db.query(models.Interview).options(
        joinedload(models.Interview.company), joinedload(models.Interview.room), joinedload(models.Interview.panel),
    ).filter(models.Interview.student_id == student_id).order_by(
        models.Interview.day, models.Interview.start_min,
    ).all()
    return [_serialize(r) for r in rows]


@router.get("/company/{company_id}")
def company_schedule(company_id: int, db: Session = Depends(get_db)):
    rows = db.query(models.Interview).options(
        joinedload(models.Interview.student), joinedload(models.Interview.room), joinedload(models.Interview.panel),
    ).filter(models.Interview.company_id == company_id).order_by(
        models.Interview.start_min,
    ).all()
    return [_serialize(r) for r in rows]
