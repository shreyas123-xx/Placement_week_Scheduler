from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import services
from ..database import get_db
from ..schemas import SeedRequest

router = APIRouter(prefix="/api/dataset", tags=["dataset"])


@router.post("/seed")
def seed(req: SeedRequest, db: Session = Depends(get_db)):
    """Generate a fresh synthetic dataset (companies, students, rooms, shortlists)."""
    stats = services.seed_database(db, seed=req.seed)
    return {"status": "seeded", **stats}


@router.post("/schedule")
def initial_schedule(db: Session = Depends(get_db)):
    """Run the initial feasible-schedule pass over the currently seeded dataset."""
    totals = services.run_initial_schedule(db)
    return {"status": "scheduled", **totals}


@router.post("/seed-and-schedule")
def seed_and_schedule(req: SeedRequest, db: Session = Depends(get_db)):
    stats = services.seed_database(db, seed=req.seed)
    totals = services.run_initial_schedule(db)
    return {"status": "ready", "dataset": stats, "schedule": totals}
