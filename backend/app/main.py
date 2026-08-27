import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, engine
from .routers import dataset, metrics, reference, replan, schedule


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Mirai Labs Placement Week Scheduler",
    description="Generates a feasible interview schedule for placement week and replans it live under disruption.",
    version="1.0.0",
    lifespan=lifespan,
)

origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dataset.router)
app.include_router(schedule.router)
app.include_router(replan.router)
app.include_router(metrics.router)
app.include_router(reference.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "days": settings.NUM_DAYS, "rooms": settings.NUM_ROOMS}


@app.get("/api/config")
def config():
    return {
        "num_days": settings.NUM_DAYS,
        "day_start_min": settings.DAY_START_MIN,
        "day_end_min": settings.DAY_END_MIN,
        "num_rooms": settings.NUM_ROOMS,
        "num_students": settings.NUM_STUDENTS,
        "num_companies": settings.NUM_COMPANIES,
    }
