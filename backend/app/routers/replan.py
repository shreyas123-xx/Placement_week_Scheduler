from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, services
from ..database import get_db
from ..schemas import (
    CompanyDelayRequest, PanelDropRequest, RoomUnavailableRequest, StudentWithdrawRequest,
)

router = APIRouter(prefix="/api/replan", tags=["replan"])


@router.post("/company-delay")
def company_delay(req: CompanyDelayRequest, db: Session = Depends(get_db)):
    try:
        return services.do_company_delay(db, req.company_id, req.delay_min)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/panel-drop")
def panel_drop(req: PanelDropRequest, db: Session = Depends(get_db)):
    try:
        return services.do_panel_drop(db, req.panel_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/student-withdraw")
def student_withdraw(req: StudentWithdrawRequest, db: Session = Depends(get_db)):
    try:
        return services.do_student_withdraw(db, req.student_id, req.withdrawal_time_min, req.day)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/room-unavailable")
def room_unavailable(req: RoomUnavailableRequest, db: Session = Depends(get_db)):
    try:
        return services.do_room_unavailable(db, req.room_id, req.day, req.start_min, req.end_min, req.reason)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/events")
def list_events(limit: int = 50, db: Session = Depends(get_db)):
    rows = db.query(models.ReplanEvent).order_by(models.ReplanEvent.id.desc()).limit(limit).all()
    return [
        {
            "id": r.id, "event_type": r.event_type, "payload": r.payload,
            "diff": r.diff, "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/events/{event_id}")
def get_event(event_id: int, db: Session = Depends(get_db)):
    r = db.get(models.ReplanEvent, event_id)
    if r is None:
        raise HTTPException(404, "event not found")
    return {
        "id": r.id, "event_type": r.event_type, "payload": r.payload,
        "diff": r.diff, "created_at": r.created_at.isoformat() if r.created_at else None,
    }
