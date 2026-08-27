"""
SchedulingWorld holds, for a single day, boolean occupancy arrays for every
room, panel and student. It is the one place that answers "is this
resource free for this stretch of time" — both the initial scheduler and
the replanner build a World from the current DB state and use the exact
same booking/lookup logic, which is what guarantees a replan can never
introduce a double-booking the initial pass wouldn't have allowed.
"""
from dataclasses import dataclass, field

from .timeutil import TOTAL_SLOTS


def _fresh_array():
    return [False] * TOTAL_SLOTS


@dataclass
class SchedulingWorld:
    day: int
    room_busy: dict = field(default_factory=dict)
    room_blocked: dict = field(default_factory=dict)
    panel_busy: dict = field(default_factory=dict)
    student_busy: dict = field(default_factory=dict)

    def ensure_room(self, room_id):
        self.room_busy.setdefault(room_id, _fresh_array())
        self.room_blocked.setdefault(room_id, _fresh_array())

    def ensure_panel(self, panel_id):
        self.panel_busy.setdefault(panel_id, _fresh_array())

    def ensure_student(self, student_id):
        self.student_busy.setdefault(student_id, _fresh_array())

    def block_room(self, room_id, start_slot: int, dur_slots: int):
        self.ensure_room(room_id)
        arr = self.room_blocked[room_id]
        for s in range(start_slot, min(start_slot + dur_slots, TOTAL_SLOTS)):
            arr[s] = True

    def _range_free(self, arr, start_slot, dur_slots):
        end = start_slot + dur_slots
        if start_slot < 0 or end > TOTAL_SLOTS:
            return False
        return not any(arr[start_slot:end])

    def panel_free(self, panel_id, start_slot, dur_slots) -> bool:
        self.ensure_panel(panel_id)
        return self._range_free(self.panel_busy[panel_id], start_slot, dur_slots)

    def room_free(self, room_id, start_slot, dur_slots) -> bool:
        self.ensure_room(room_id)
        if not self._range_free(self.room_busy[room_id], start_slot, dur_slots):
            return False
        return self._range_free(self.room_blocked[room_id], start_slot, dur_slots)

    def student_free(self, student_id, start_slot, dur_slots) -> bool:
        self.ensure_student(student_id)
        return self._range_free(self.student_busy[student_id], start_slot, dur_slots)

    def is_free(self, student_id, panel_id, room_id, start_slot, dur_slots) -> bool:
        return (
            self.panel_free(panel_id, start_slot, dur_slots)
            and self.room_free(room_id, start_slot, dur_slots)
            and self.student_free(student_id, start_slot, dur_slots)
        )

    def book(self, student_id, panel_id, room_id, start_slot, dur_slots):
        self.ensure_panel(panel_id)
        self.ensure_room(room_id)
        self.ensure_student(student_id)
        end = start_slot + dur_slots
        for s in range(start_slot, end):
            self.panel_busy[panel_id][s] = True
            self.room_busy[room_id][s] = True
            self.student_busy[student_id][s] = True

    def release(self, student_id, panel_id, room_id, start_slot, dur_slots):
        end = start_slot + dur_slots
        if panel_id is not None:
            self.ensure_panel(panel_id)
            for s in range(start_slot, end):
                self.panel_busy[panel_id][s] = False
        if room_id is not None:
            self.ensure_room(room_id)
            for s in range(start_slot, end):
                self.room_busy[room_id][s] = False
        if student_id is not None:
            self.ensure_student(student_id)
            for s in range(start_slot, end):
                self.student_busy[student_id][s] = False

    def find_slot(
        self, student_id, panel_ids, room_ids, dur_slots, earliest_slot, latest_slot_exclusive,
    ):
        """
        First-fit search: earliest start slot (ascending) at which SOME panel
        from panel_ids and SOME room from room_ids are both free alongside
        the student. Returns (panel_id, room_id, start_slot) or None.

        First-fit (rather than e.g. random or best-fit) is a deliberate
        choice: it minimises student waiting time (metric #4) by always
        taking the earliest opportunity, and it is what makes replans
        stable — re-running the same search after a small change tends to
        reproduce most of the original schedule instead of shuffling it.
        """
        for start in range(earliest_slot, latest_slot_exclusive - dur_slots + 1):
            if not self.student_free(student_id, start, dur_slots):
                continue
            for panel_id in panel_ids:
                if not self.panel_free(panel_id, start, dur_slots):
                    continue
                for room_id in room_ids:
                    if self.room_free(room_id, start, dur_slots):
                        return panel_id, room_id, start
        return None
