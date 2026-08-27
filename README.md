# Placement Week Scheduler

Technical assessment (Assignment A). Generates a realistic
placement-week dataset, produces the best feasible interview schedule it can,
and replans live under disruption with a minimal-diff change summary — the
system a coordinator would actually run from a laptop on the day.

**Stack:** FastAPI (Python) · MySQL 8 · React (Vite) + Tailwind.

```
┌─────────────┐      REST/JSON       ┌──────────────┐      SQLAlchemy      ┌────────┐
│   React UI  │ ───────────────────► │   FastAPI    │ ───────────────────► │  MySQL │
│ (dashboard) │ ◄─────────────────── │  + scheduler │ ◄─────────────────── │        │
└─────────────┘                      │  + replanner │                      └────────┘
                                      └──────────────┘
```

---

## Quick start

### Option A — one command (Docker)

```bash
docker compose up --build
```

- Frontend: http://localhost:8080
- Backend docs: http://localhost:8000/docs
- MySQL: localhost:3306 (user/pass `scheduler`/`scheduler`, db `placement_scheduler`)

First load will show a "Generate placement week" screen — click it once. That's
the whole setup.

### Option B — run locally without Docker

```bash
# MySQL: point DATABASE_URL at any MySQL 8 instance you have, or use SQLite for a
# quick spin: export DATABASE_URL="sqlite:///./dev.db"

cd backend
pip install -r requirements.txt
cp .env.example .env   # edit DATABASE_URL
uvicorn app.main:app --reload

# separate terminal
cd frontend
npm install
cp .env.example .env
npm run dev             # http://localhost:5173
```

### Running the tests

```bash
cd backend
pip install -r requirements.txt pytest httpx
python -m pytest tests/ -v
```

`tests/test_scheduling_engine.py` and `tests/test_replanner.py` are pure unit
tests (no DB) that assert, among other things, **zero double-booking** across
thousands of generated interviews and every replan type. `tests/test_api_integration.py`
drives the real FastAPI app end-to-end against a throwaway SQLite file
(seed → schedule → all 4 disruptions → re-verify no overlaps).


## What's actually inside

* **Generator** — 35 companies / 800 students / 20 rooms / 4 days with realistic skew (Day-1 mass recruiters, CGPA-weighted overlapping shortlists, branch-focused core companies).

* **Scheduler** — a greedy, priority-ordered, first-fit heuristic (deliberately not an ILP — defended in `Approach_and_Defense.md`) that guarantees zero double-booking by construction, and diagnoses why each unschedulable interview failed (room scarcity vs. panel capacity vs. student clash) instead of failing silently.

* **Replanner** — all four required disruptions (company delay, panel drop, student withdrawal with waitlist backfill, room unavailability), each doing minimal-disturbance local repair with a full before/after diff and a `churn_pct` metric.

* **Metrics** — completion rate, room/panel utilization, avg student wait, replan churn — the "what does good mean" question answered concretely.

* **Dashboard** — a control-room-styled React UI (split-flap live board, disruption triggers with diff viewer, unscheduled report, company/student explorers, full replan audit history).

---

