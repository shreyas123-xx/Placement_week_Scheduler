from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..core import metrics as metrics_core
from ..database import get_db

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("/summary")
def summary(db: Session = Depends(get_db)):
    return metrics_core.full_summary(db)


@router.get("/room-utilization/{day}")
def room_util(day: int, db: Session = Depends(get_db)):
    return metrics_core.room_utilization(db, day)


@router.get("/panel-utilization/{day}")
def panel_util(day: int, db: Session = Depends(get_db)):
    return metrics_core.panel_utilization_by_company(db, day)


@router.get("/student-wait/{day}")
def student_wait(day: int, db: Session = Depends(get_db)):
    return metrics_core.avg_student_wait_minutes(db, day)
