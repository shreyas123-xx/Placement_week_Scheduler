# System Architecture & Technical Defense

This document outlines the core architectural decisions, algorithm choices, and trade-offs made while building the Placement Week Scheduler. 

While the `README.md` focuses purely on operational instructions and getting the application running, this write-up serves as a technical defense of the system's design. It addresses the explicit constraints of the assignment, explains the logic behind the custom scheduling engine and justifies the minimal-disturbance strategy used for live replanning.

---

## 1. The dataset generator (`backend/app/core/generator.py`)

Realism decisions, since the brief grades this explicitly:

- **Day 1 is mass-recruiter-heavy.** ~34% of companies are "mass" tier (low
  CGPA cutoff, 3–6 panels, 10–20 min interviews, 90–200 student shortlists)
  and are weighted to land on Day 1. "Dream" tier companies (high cutoff,
  1–3 panels, 30–45 min interviews, small shortlists) skew toward Days 3–4,
  the way real recruiting cycles put brand-name/selective companies later
  once students already hold offers.
- **Shortlists overlap the way real ones do.** A student's chance of being on
  a company's shortlist is weighted by how far their CGPA sits above that
  company's cutoff (with a small chance below it too, modelling branch quotas
  / diversity carve-outs), so strong students land on many companies' lists
  and the schedule has genuine, unavoidable contention for their time —
  exactly the "top students appear on many overlapping lists" the brief asks
  for.
- **Branch mix is CS/IT-heavy** (matching typical tech-recruiter eligibility
  pools), and core companies recruit from a narrower set of branches while
  mass recruiters take almost anyone.
- Every company gets its own **time window** within the day (full day or a
  half-day slot), not just a slot count, because that's what actually limits
  how many interviews a company with N panels can run.

Regenerate with a different sample via `POST /api/dataset/seed` (`{"seed": 123}`)
or the "Regenerate dataset" button in the UI header.

---

## 2. The scheduling algorithm (`backend/app/core/scheduling_engine.py`)

**This is a greedy, priority-ordered, first-fit heuristic — not an exact
CSP/ILP solver.** That's a deliberate call, worth defending up front:

- At this scale (thousands of interviews; tens of thousands of
  student/panel/room combinations) an ILP formulation is solvable, but a
  coordinator standing in front of a 3-hour delay does not want to wait for
  a solver to re-optimize — they want an answer in well under a second.
  Every replan in this system runs in a few hundred milliseconds because
  it's the same booking primitive as the initial pass, not a second
  algorithm bolted onto an optimizer's output.
- The heuristic's decisions are **legible**: every unschedulable interview
  gets a specific, human-readable reason (see below) derived directly from
  which constraint the search actually hit. An ILP's infeasibility
  certificate or dual values would not translate into "tell the coordinator
  why" nearly as directly.
- The trade-off is optimality: a solver might squeeze out a few more percent
  scheduled in the tightest cases. Given the brief's own framing — "a perfect
  schedule is usually impossible" — legibility and speed under disruption
  matter more here than the last few points of completion.

**Ordering choices (the two heuristics that matter most):**

1. **Companies are scheduled most-oversubscribed-first.** For each company we
   compute `shortlist_size / (panels × window_capacity)`. Companies whose own
   demand most exceeds their own supply go first, so they get first claim on
   shared students' free time. Scheduling the roomiest companies first would
   let them opportunistically "steal" slots from a tightly-constrained
   company purely by going first — that's not a coordinator's actual
   priority.
2. **Within a company, the most-contested students go first** — students
   shortlisted by the most *other* companies on the same day, since they're
   the ones most likely to run out of common free time. Ties are otherwise
   unordered (no CGPA-based favoritism beyond what shortlisting itself
   already encodes).
3. **First-fit, earliest slot.** When searching for a (panel, room, time),
   the algorithm takes the *first* feasible slot rather than an optimal one.
   This minimizes student waiting time by construction (metric #4 below) and
   is what makes replans stable: re-running the search after a small change
   tends to reproduce most of the original schedule instead of reshuffling
   it.

**Infeasibility is diagnosed, never silent.** When no slot exists for a
(company, student) pair, the algorithm re-probes the search space to
determine *why*:

- `"company's panels are fully booked in their allotted window"` — the
  company itself doesn't have enough panel-time for its own shortlist.
- `"student has clashing interviews with other companies at every mutual
  free slot"` — the panel had room, but the student didn't.
- `"panel and student were both free at some point, but no room was free at
  the same time"` — the campus is out of physical rooms at that moment.

At 800 students / 35 companies / 20 rooms these three reasons show up in
different proportions on different days, which is itself informative: see
the Overview tab, where Day 1's near-100% room utilization with low
completion tells the coordinator "buy more rooms" would help far more than
"tune the algorithm" would.

---

## 3. Replanning (`backend/app/core/replanner.py`) — the heart of the assignment

The brief's own line is the design spec: *"Moving 200 appointments to fix a
2-hour delay is technically valid and practically a disaster."* Every repair
function follows the same discipline:

1. **Touch only what the disruption actually invalidates** — never
   re-run the whole day's schedule. A company delay only looks at that
   company's interviews that now start before its new window; a panel
   drop only looks at that panel's interviews; a room block only looks at
   interviews overlapping the blocked window in that room.
2. **Prefer the smallest possible repair first.** Panel drop and room
   unavailability both try "same time slot, alternate panel/room" *before*
   falling back to a wider time search — so most affected interviews change
   only one field, not their whole slot.
3. **Preserve chronological order** when multiple interviews of the same
   company must move, so a student's afternoon doesn't get shuffled for no
   reason.
4. **Never fail silently.** Anything that can't be repaired becomes
   `newly_unscheduled` with a reason, exactly like the initial pass.

Implemented disruptions (`POST /api/replan/...`):

| Disruption | Endpoint | What moves |
|---|---|---|
| Company arrives late | `/company-delay` | Only that company's interviews that no longer fit before the new (shifted) window start. A 60-minute campus-wide grace window past the official day end absorbs small delays before anything is reported unscheduled. |
| Panel drops out | `/panel-drop` | Only that panel's interviews; remaining panels of the *same* company absorb them, same-slot-different-panel first. |
| Student withdraws | `/student-withdraw` | Only that student's *future* interviews (an optional `withdrawal_time_min` protects ones that already happened). Freed slots are **backfilled** from that company's waitlist where a match exists — a student who couldn't get a slot at 9am might now get the exact one just vacated. |
| Room becomes unavailable | `/room-unavailable` | Only interviews overlapping the blocked window in that room; same-slot-different-room first. |

Every replan returns (and permanently logs, via `ReplanEvent`) a diff:

```json
{
  "reason_summary": "Company 7 delayed 180 min on day 1",
  "counts": {"moved": 11, "newly_unscheduled": 4},
  "changes": [{"interview_id": 812, "student_id": 233, "change_type": "moved",
               "before": {...}, "after": {...}}],
  "affected_students": [1, 2, 3],
  "affected_companies": [7],
  "churn_pct": 1.9
}
```

`churn_pct` (changed interviews ÷ previously-scheduled interviews for that
day) is the number a coordinator should actually watch: a delay that churns
2% of the day is safe to auto-apply; one that churns 40% needs a human look
before it's rolled out. This is also the number we'd use, if extended, to
decide automatically whether to apply a repair or just present it as a
proposal.

---

## 4. Metrics — what "good" means here (`backend/app/core/metrics.py`)

| Metric | What it tells the coordinator |
|---|---|
| **Completion rate** | headline: what fraction of required interviews got a room+panel+time. |
| **Room utilization** | read *together with* completion: high utilization + low completion means the campus is genuinely out of rooms that day — buying more rooms helps; tuning the algorithm won't. |
| **Panel utilization (per company)** | a company sitting at 40% utilization with unscheduled students usually means its own shortlist is badly time-boxed, not that the day is infeasible. |
| **Avg. student wait time** | a schedule can hit 100% completion and still be bad for people if it leaves them idle for hours between rounds. |
| **Replan churn %** | how much of a previously-settled schedule a disruption's fix touched — the number that decides whether a replan is safe to auto-apply. |

All five are visible in the Overview tab and the `/api/metrics/*` endpoints.

---

## 5. Decisions defended (per the brief's explicit prompts)

**What does a "good" schedule mean?** See the metrics table above — we don't
collapse it to one number. Completion rate is the headline, but it's read
alongside room/panel utilization (is the bottleneck supply or the
algorithm?) and student wait time (is it fair to the people in it?).

**When infeasible, which constraint bends first, and who decides?** The
system never silently drops a constraint — room, panel, and student
double-booking are hard constraints, enforced structurally by
`SchedulingWorld` (there's no code path that can violate them; see the
overlap-assertion tests). What bends is *whose interview doesn't get a
slot* — and that's a policy choice we make explicit rather than hide: within
a company, higher-contention students are prioritized (see §2). We do **not**
silently reprioritize by CGPA or company tier beyond what the generator's
own shortlist weighting already encodes — that's a policy lever a real
coordinator should set (e.g. "always protect Dream-tier interviews first"),
and the architecture supports it as a one-line change to `_company_order` /
`_student_order_for_company` if the coordinator wants that policy instead.
We report exactly what didn't get scheduled and why, and leave the judgment
call of *accepting* that trade-off to the coordinator, not the algorithm.

**How much reshuffling is acceptable during a replan?** Answered structurally
in §3 (touch only what's invalidated, prefer the smallest repair, preserve
order) and quantified via `churn_pct` on every replan result, rather than
left as a vague goal.

---

## 6. Live-defense scenario walkthrough

The brief describes: *"the biggest Day-1 recruiter is 3 hours late, one of
its panels dropped, and 15 students just withdrew."* Reproducing it:

1. Open **Companies** tab, sort/filter to Day 1, find the largest
   `shortlist_size`.
2. **Disruptions → Company arrives late** → select it → drag to 180 min →
   Replan. Watch the diff: only interviews that no longer fit before the new
   window (plus a 60-min grace period) move or fall out.
3. **Disruptions → A panel drops out** → same company → pick one of its
   panels → Replan. Most affected interviews keep their original time slot
   and room, only the panel changes.
4. **Disruptions → Student withdraws** → repeat for ~15 students who were on
   that company's roster (Companies tab → click through to their schedule,
   or just search by name in Students). Watch for `backfilled` entries where
   a waitlisted student got the freed slot.
5. **History** tab shows the full audit trail of everything just done, each
   with its own diff and churn %, ready to read out during defense.

---

## 7. API reference (summary — full interactive docs at `/docs`)

```
POST /api/dataset/seed                  regenerate companies/students/rooms/shortlists
POST /api/dataset/schedule              run the initial feasible-schedule pass
POST /api/dataset/seed-and-schedule     both, in one call

GET  /api/schedule                      filter by day/company_id/student_id/room_id/status
GET  /api/schedule/unscheduled          grouped-by-company infeasibility report
GET  /api/schedule/student/{id}         one student's full week
GET  /api/schedule/company/{id}         one company's full roster

POST /api/replan/company-delay          {company_id, delay_min}
POST /api/replan/panel-drop             {panel_id}
POST /api/replan/student-withdraw       {student_id, day, withdrawal_time_min?}
POST /api/replan/room-unavailable       {room_id, day, start_min, end_min, reason?}
GET  /api/replan/events                 full audit trail

GET  /api/metrics/summary               everything the Overview tab renders
GET  /api/companies /students /rooms /panels   reference data + search
```

---

## 8. Known limitations / what we'd do next

- The scheduler is per-day-independent (a company only runs on one day, so
  cross-day student conflicts can't occur) — this is a real simplification
  that happens to match the brief's scenario, but a multi-day company would
  need the `SchedulingWorld` extended to span days.
- Replan policy (who gets bumped) is currently "most-contested-student-first,
  no tier-based protection." Making tier protection (e.g. "never bump a
  Dream-tier interview to backfill a Mass-tier one") a coordinator-configurable
  policy is the natural next step and requires no architecture change, just
  parameterizing `_student_order_for_company`.
- No authentication — this is a single-coordinator tool as specified, not a
  multi-tenant product.
- Backfill during student withdrawal only tries the exact freed slot; it
  doesn't attempt a cascading re-optimization of the whole waitlist, again
  in the interest of bounded, explainable replan latency.
