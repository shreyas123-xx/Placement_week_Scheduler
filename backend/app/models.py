"""
Relational schema.

Design notes (worth reading before touching the scheduler):

- Time is stored as (day, slot_index) where slot_index is an integer offset
  in SLOT_GRANULARITY_MIN chunks from DAY_START_MIN. This makes overlap
  checks integer range comparisons instead of datetime arithmetic, which
  matters because the scheduler does thousands of them.

- `Interview` is the single source of truth for "who is where, when".
  Every constraint (room, panel, student) is checked against this one
  table, so there is exactly one place double-booking can be introduced
  and exactly one place it can be prevented.

- Nothing is ever deleted from `Interview` after the initial generation.
  Replanning changes status/day/slot/room/panel on existing rows and
  writes a row to `ReplanEvent` describing the diff. This gives us a full
  audit trail for the dashboard ("who needs to be informed") without a
  separate history table.
"""
import enum

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, ForeignKey, Enum, Text, JSON,
    DateTime, UniqueConstraint, Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


class PriorityTier(str, enum.Enum):
    DREAM = "dream"      # very selective, few slots, high cutoff
    CORE = "core"        # mid-size recruiters
    MASS = "mass"        # Day-1 bulk recruiters (TCS/Infosys-style)


class PanelStatus(str, enum.Enum):
    ACTIVE = "active"
    DROPPED = "dropped"


class InterviewStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    UNSCHEDULED = "unscheduled"   # never found a slot in the initial pass
    CANCELLED = "cancelled"       # withdrawn / dropped by a replan


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    day = Column(Integer, nullable=False)                 # 1..NUM_DAYS
    priority_tier = Column(Enum(PriorityTier), nullable=False)
    cgpa_cutoff = Column(Float, nullable=False)
    interview_duration_min = Column(Integer, nullable=False)
    window_start_min = Column(Integer, nullable=False)     # company's own slot within the day
    window_end_min = Column(Integer, nullable=False)
    num_panels = Column(Integer, nullable=False)
    # mutable event-day fields:
    delay_min = Column(Integer, nullable=False, default=0)
    is_late = Column(Boolean, nullable=False, default=False)

    panels = relationship("Panel", back_populates="company", cascade="all, delete-orphan")
    shortlists = relationship("Shortlist", back_populates="company", cascade="all, delete-orphan")
    interviews = relationship("Interview", back_populates="company")


class Panel(Base):
    __tablename__ = "panels"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    panel_number = Column(Integer, nullable=False)
    status = Column(Enum(PanelStatus), nullable=False, default=PanelStatus.ACTIVE)

    company = relationship("Company", back_populates="panels")

    __table_args__ = (UniqueConstraint("company_id", "panel_number", name="uq_panel_company_number"),)


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True)
    roll_no = Column(String(20), nullable=False, unique=True)
    name = Column(String(120), nullable=False)
    cgpa = Column(Float, nullable=False)
    branch = Column(String(10), nullable=False)
    withdrawn = Column(Boolean, nullable=False, default=False)
    withdrawn_at_min = Column(Integer, nullable=True)  # absolute campus-minute they withdrew, if applicable

    shortlists = relationship("Shortlist", back_populates="student", cascade="all, delete-orphan")
    interviews = relationship("Interview", back_populates="student")


class Shortlist(Base):
    """Company X shortlisted student Y. Independent of whether it got scheduled."""
    __tablename__ = "shortlists"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)

    company = relationship("Company", back_populates="shortlists")
    student = relationship("Student", back_populates="shortlists")

    __table_args__ = (UniqueConstraint("company_id", "student_id", name="uq_shortlist_company_student"),)


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True)
    name = Column(String(20), nullable=False, unique=True)
    capacity = Column(Integer, nullable=False, default=1)


class RoomBlock(Base):
    """A room made unavailable for a window (a disruption artifact)."""
    __tablename__ = "room_blocks"

    id = Column(Integer, primary_key=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    day = Column(Integer, nullable=False)
    start_min = Column(Integer, nullable=False)
    end_min = Column(Integer, nullable=False)
    reason = Column(String(255), nullable=True)


class Interview(Base):
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    panel_id = Column(Integer, ForeignKey("panels.id"), nullable=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=True)

    day = Column(Integer, nullable=True)
    start_min = Column(Integer, nullable=True)   # absolute minute within the day
    end_min = Column(Integer, nullable=True)

    status = Column(Enum(InterviewStatus), nullable=False, default=InterviewStatus.UNSCHEDULED)
    unscheduled_reason = Column(String(255), nullable=True)

    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    company = relationship("Company", back_populates="interviews")
    student = relationship("Student", back_populates="interviews")
    panel = relationship("Panel")
    room = relationship("Room")

    __table_args__ = (
        Index("ix_interview_company_student", "company_id", "student_id"),
        Index("ix_interview_day_room", "day", "room_id"),
        Index("ix_interview_day_panel", "day", "panel_id"),
        Index("ix_interview_day_student", "day", "student_id"),
    )


class ReplanEvent(Base):
    """Audit trail: every disruption + the diff it produced."""
    __tablename__ = "replan_events"

    id = Column(Integer, primary_key=True)
    event_type = Column(String(40), nullable=False)
    payload = Column(JSON, nullable=False)
    diff = Column(JSON, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
