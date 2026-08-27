import math

from ..config import settings

GRAN = settings.SLOT_GRANULARITY_MIN
DAY_START = settings.DAY_START_MIN
DAY_END = settings.DAY_END_MIN
DAY_END_WITH_SPILLOVER = settings.DAY_END_MIN + settings.MAX_SPILLOVER_MIN

# Total slots in the array each resource-per-day tracker allocates. Extended
# past the official day end so a delay replan has somewhere to search before
# giving up and reporting the interview as unscheduled.
TOTAL_SLOTS = (DAY_END_WITH_SPILLOVER - DAY_START) // GRAN


def minute_to_slot(minute: int) -> int:
    return (minute - DAY_START) // GRAN


def slot_to_minute(slot: int) -> int:
    return DAY_START + slot * GRAN


def duration_to_slots(duration_min: int) -> int:
    return math.ceil(duration_min / GRAN)


def fmt_minute(minute: int) -> str:
    h, m = divmod(minute, 60)
    return f"{h:02d}:{m:02d}"
