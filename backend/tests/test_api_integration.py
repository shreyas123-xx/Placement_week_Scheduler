"""
Full-stack (minus the browser) smoke test: spins the real FastAPI app up
against a throwaway SQLite file, seeds a smaller synthetic dataset (same
generator/scheduler/replanner code path as production, just fewer rows so
the test runs in seconds), and exercises seed -> schedule -> all four
disruption types -> metrics, asserting the API contract holds and nothing
double-books along the way.
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_integration.db"
os.environ["NUM_STUDENTS"] = "120"
os.environ["NUM_COMPANIES"] = "10"
os.environ["NUM_ROOMS"] = "6"
os.environ["RANDOM_SEED"] = "1"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

if os.path.exists("./test_integration.db"):
    os.remove("./test_integration.db")

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)
client.__enter__()  # trigger lifespan startup (creates tables)


def test_full_flow():
    r = client.get("/api/health")
    assert r.status_code == 200

    r = client.post("/api/dataset/seed-and-schedule", json={"seed": 1})
    assert r.status_code == 200
    body = r.json()
    assert body["dataset"]["students"] == 120
    assert body["dataset"]["companies"] == 10
    assert body["schedule"]["scheduled"] + body["schedule"]["unscheduled"] == body["dataset"]["shortlists"]

    # ---- schedule listing works and is internally consistent ----
    r = client.get("/api/schedule", params={"status": "scheduled", "limit": 5000})
    assert r.status_code == 200
    scheduled = r.json()
    assert len(scheduled) == body["schedule"]["scheduled"]

    # no double booking across the whole generated dataset
    seen_panel, seen_room, seen_student = set(), set(), set()
    for iv in scheduled:
        for bucket, key in (
            (seen_panel, (iv["panel_id"], iv["day"])),
            (seen_room, (iv["room_id"], iv["day"])),
            (seen_student, (iv["student_id"], iv["day"])),
        ):
            span = (iv["start_min"], iv["end_min"])
            for other_span in list(bucket):
                if other_span[0] == key:
                    s0, e0 = other_span[1]
                    assert e0 <= span[0] or span[1] <= s0, f"overlap detected: {key} {other_span} vs {span}"
            bucket.add((key, span))

    # ---- unscheduled report is non-empty-reasoned ----
    r = client.get("/api/schedule/unscheduled")
    assert r.status_code == 200
    for group in r.json():
        assert group["count"] > 0
        assert all(reason for reason in group["reasons"].keys())

    # ---- metrics summary ----
    r = client.get("/api/metrics/summary")
    assert r.status_code == 200
    summary = r.json()
    assert summary["overall"]["total_required"] == body["dataset"]["shortlists"]

    # ---- disruption 1: company delay ----
    companies = client.get("/api/companies").json()
    target_company = next(c for c in companies if c["shortlist_size"] > 0)
    r = client.post("/api/replan/company-delay", json={"company_id": target_company["id"], "delay_min": 90})
    assert r.status_code == 200
    diff = r.json()
    assert "counts" in diff
    assert diff["churn_pct"] < 100  # sanity: shouldn't touch >100% of anything

    # ---- disruption 2: panel drop ----
    panels = client.get("/api/panels", params={"company_id": target_company["id"]}).json()
    active_panel = next((p for p in panels if p["status"] == "active"), None)
    if active_panel:
        r = client.post("/api/replan/panel-drop", json={"panel_id": active_panel["id"]})
        assert r.status_code == 200

    # ---- disruption 3: student withdraw ----
    students = client.get("/api/students", params={"limit": 5}).json()
    r = client.post("/api/replan/student-withdraw", json={
        "student_id": students[0]["id"], "day": target_company["day"], "withdrawal_time_min": None,
    })
    assert r.status_code == 200

    # ---- disruption 4: room unavailable ----
    rooms = client.get("/api/rooms").json()
    r = client.post("/api/replan/room-unavailable", json={
        "room_id": rooms[0]["id"], "day": target_company["day"],
        "start_min": 540, "end_min": 600, "reason": "AV equipment failure",
    })
    assert r.status_code == 200

    # ---- replan events were logged ----
    r = client.get("/api/replan/events")
    assert r.status_code == 200
    events = r.json()
    assert len(events) == 4
    event_types = {e["event_type"] for e in events}
    assert event_types == {"company_delay", "panel_drop", "student_withdraw", "room_unavailable"}

    # ---- after all replans, still no double-booking anywhere ----
    r = client.get("/api/schedule", params={"status": "scheduled", "limit": 5000})
    scheduled_after = r.json()
    seen = {}
    for iv in scheduled_after:
        for kind, rid in (("panel", iv["panel_id"]), ("room", iv["room_id"]), ("student", iv["student_id"])):
            key = (kind, rid, iv["day"])
            span = (iv["start_min"], iv["end_min"])
            for other in seen.get(key, []):
                assert other[1] <= span[0] or span[1] <= other[0], f"post-replan overlap: {key}"
            seen.setdefault(key, []).append(span)

    print("\nFinal metrics summary:", client.get("/api/metrics/summary").json()["overall"])


if __name__ == "__main__":
    test_full_flow()
    print("OK")
