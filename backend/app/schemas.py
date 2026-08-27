from typing import Optional

from pydantic import BaseModel


class SeedRequest(BaseModel):
    seed: Optional[int] = None


class CompanyDelayRequest(BaseModel):
    company_id: int
    delay_min: int


class PanelDropRequest(BaseModel):
    panel_id: int


class StudentWithdrawRequest(BaseModel):
    student_id: int
    day: int
    withdrawal_time_min: Optional[int] = None


class RoomUnavailableRequest(BaseModel):
    room_id: int
    day: int
    start_min: int
    end_min: int
    reason: Optional[str] = "room unavailable"
