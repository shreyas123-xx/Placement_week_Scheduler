from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from .. import models
from ..database import get_db

router = APIRouter(prefix="/api", tags=["reference"])


@router.get("/companies")
def list_companies(day: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(models.Company).options(joinedload(models.Company.panels), joinedload(models.Company.shortlists))
    if day is not None:
        q = q.filter(models.Company.day == day)
    companies = q.order_by(models.Company.day, models.Company.name).all()
    out = []
    for c in companies:
        out.append({
            "id": c.id, "name": c.name, "day": c.day, "tier": c.priority_tier.value,
            "cgpa_cutoff": c.cgpa_cutoff, "interview_duration_min": c.interview_duration_min,
            "window_start_min": c.window_start_min, "window_end_min": c.window_end_min,
            "num_panels": c.num_panels, "delay_min": c.delay_min, "is_late": c.is_late,
            "shortlist_size": len(c.shortlists),
            "panels": [{"id": p.id, "panel_number": p.panel_number, "status": p.status.value} for p in c.panels],
        })
    return out


@router.get("/companies/{company_id}")
def get_company(company_id: int, db: Session = Depends(get_db)):
    c = db.query(models.Company).options(
        joinedload(models.Company.panels), joinedload(models.Company.shortlists),
    ).get(company_id)
    if c is None:
        return {"error": "not found"}
    return {
        "id": c.id, "name": c.name, "day": c.day, "tier": c.priority_tier.value,
        "cgpa_cutoff": c.cgpa_cutoff, "interview_duration_min": c.interview_duration_min,
        "window_start_min": c.window_start_min, "window_end_min": c.window_end_min,
        "num_panels": c.num_panels, "delay_min": c.delay_min, "is_late": c.is_late,
        "shortlist_size": len(c.shortlists),
        "panels": [{"id": p.id, "panel_number": p.panel_number, "status": p.status.value} for p in c.panels],
    }


@router.get("/students")
def list_students(
    q: Optional[str] = None, branch: Optional[str] = None, limit: int = 50,
    db: Session = Depends(get_db),
):
    query = db.query(models.Student)
    if q:
        like = f"%{q}%"
        query = query.filter((models.Student.name.ilike(like)) | (models.Student.roll_no.ilike(like)))
    if branch:
        query = query.filter(models.Student.branch == branch)
    rows = query.order_by(models.Student.name).limit(limit).all()
    return [
        {"id": s.id, "name": s.name, "roll_no": s.roll_no, "cgpa": s.cgpa,
         "branch": s.branch, "withdrawn": s.withdrawn}
        for s in rows
    ]


@router.get("/rooms")
def list_rooms(db: Session = Depends(get_db)):
    rows = db.query(models.Room).order_by(models.Room.name).all()
    return [{"id": r.id, "name": r.name, "capacity": r.capacity} for r in rows]


@router.get("/panels")
def list_panels(company_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(models.Panel).options(joinedload(models.Panel.company))
    if company_id is not None:
        q = q.filter(models.Panel.company_id == company_id)
    rows = q.all()
    return [
        {"id": p.id, "company_id": p.company_id, "company_name": p.company.name if p.company else None,
         "panel_number": p.panel_number, "status": p.status.value}
        for p in rows
    ]
