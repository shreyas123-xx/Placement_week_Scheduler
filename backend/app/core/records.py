from dataclasses import dataclass


@dataclass
class InterviewRecord:
    id: int
    company_id: int
    student_id: int
    panel_id: int | None
    room_id: int | None
    day: int | None
    start_min: int | None
    end_min: int | None
    status: str  # "scheduled" | "unscheduled" | "cancelled"
    unscheduled_reason: str | None = None
