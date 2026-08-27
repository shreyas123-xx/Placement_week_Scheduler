"""
Synthetic-but-realistic placement week dataset.

The grading brief is explicit that the *realism* of this data matters, so
the generator encodes a handful of things that are true of real placement
seasons rather than sampling everything uniformly:

  * Day 1 is dominated by mass recruiters (bulk hiring, low CGPA cutoff,
    huge shortlists, short interviews, many panels running in parallel).
    Dream companies cluster on the later days once students have offers
    from Day 1 and are choosier, which is also why dream-company interview
    slots are longer (case rounds / multiple technical rounds back to back
    are modelled as one long slot for simplicity).

  * A student's chance of being shortlisted by a company is driven by
    their CGPA relative to that company's cutoff, with a soft margin
    (some slack above/below the cutoff, not a hard cliff) so shortlists
    overlap the way they really do: strong students end up on many lists,
    weak students end up on few.

  * Branch mix is CS/IT heavy (reflecting typical eligibility pools for
    tech recruiters) with other branches represented but thinner, and a
    company's shortlist is weighted toward the branches it actually
    recruits for (core companies skew EEE/ECE/MECH, mass IT recruiters
    take almost any branch).
"""
import random
from dataclasses import dataclass, field

from ..config import settings
from ..models import PriorityTier

BRANCHES_WEIGHTED = [
    ("CSE", 30), ("IT", 20), ("ECE", 18), ("EEE", 10),
    ("MECH", 10), ("CIVIL", 6), ("CHEM", 3), ("BIOTECH", 3),
]

COMPANY_NAME_POOL = [
    "Tectonic Systems", "Alluvium Analytics", "NimbusEdge", "Faircode Labs",
    "Vertex Retail Tech", "Orbital Fintech", "Kestrel Robotics", "Havenware",
    "Ridgeline Cloud", "BrightAxis", "Coral Networks", "Lumen Chip Design",
    "Ferro Manufacturing", "Solace Health Systems", "Quill & Ledger Consulting",
    "Marrow Biosciences", "Anchorpoint Logistics", "Trellis Data", "Northwind Energy",
    "Pallet Commerce", "Ironclad Defense Systems", "Gable Insurance Tech",
    "Cinder Semiconductors", "Wavecrest Telecom", "Almanac EdTech",
    "Foundry Automotive", "Pinehurst Capital", "Driftwood Media Tech",
    "Silo AgriTech", "Cobalt Aerospace", "Meridian Public Sector Tech",
    "Thistle Pharma", "Greywolf Cybersecurity", "Lattice Semiconductor",
    "Basalt Infrastructure", "Amberlight Studios", "Cascade Water Systems",
    "Fjord Maritime Tech", "Hearth Consumer Goods", "Talon Aviation",
]

FIRST_NAMES = [
    "Aarav", "Vihaan", "Aditi", "Diya", "Kabir", "Ishaan", "Ananya", "Myra",
    "Reyansh", "Sai", "Arjun", "Kiara", "Vivaan", "Anika", "Rohan", "Meera",
    "Karthik", "Priya", "Nikhil", "Sneha", "Arnav", "Tara", "Yash", "Riya",
    "Devansh", "Pooja", "Aryan", "Ira", "Sarthak", "Naina", "Om", "Zara",
    "Krish", "Aisha", "Dhruv", "Kavya", "Manav", "Lavanya", "Rudra", "Sana",
]
LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Iyer", "Nair", "Reddy", "Rao", "Patel",
    "Menon", "Pillai", "Kulkarni", "Joshi", "Chatterjee", "Das", "Bose",
    "Mukherjee", "Agarwal", "Bhat", "Shetty", "Choudhary", "Malhotra", "Kapoor",
]


@dataclass
class GenCompany:
    name: str
    day: int
    priority_tier: PriorityTier
    cgpa_cutoff: float
    interview_duration_min: int
    window_start_min: int
    window_end_min: int
    num_panels: int
    branch_focus: list = field(default_factory=list)  # empty == recruits any branch


@dataclass
class GenStudent:
    roll_no: str
    name: str
    cgpa: float
    branch: str


def _weighted_choice(rng: random.Random, pairs):
    total = sum(w for _, w in pairs)
    r = rng.uniform(0, total)
    upto = 0
    for val, w in pairs:
        upto += w
        if upto >= r:
            return val
    return pairs[-1][0]


def _clip(v, lo, hi):
    return max(lo, min(hi, v))


def generate_students(rng: random.Random, n: int) -> list[GenStudent]:
    students = []
    used_names = set()
    for i in range(1, n + 1):
        branch = _weighted_choice(rng, BRANCHES_WEIGHTED)
        cgpa = _clip(round(rng.normalvariate(7.2, 0.9), 2), 5.0, 10.0)
        while True:
            name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
            key = (name, i)
            if key not in used_names:
                used_names.add(key)
                break
        roll_no = f"{2023 + rng.randint(0, 1)}{branch[:2]}{i:04d}"
        students.append(GenStudent(roll_no=roll_no, name=name, cgpa=cgpa, branch=branch))
    return students


def generate_companies(rng: random.Random, n: int, num_days: int) -> list[GenCompany]:
    companies = []
    names = rng.sample(COMPANY_NAME_POOL, min(n, len(COMPANY_NAME_POOL)))
    while len(names) < n:  # in case n > pool size
        names.append(f"{rng.choice(COMPANY_NAME_POOL)} ({len(names)})")

    # Day 1 is mass-recruiter heavy; dream companies skew later days.
    # We assign a day per company using a tier-conditioned distribution.
    for i, name in enumerate(names):
        day = None
        tier_roll = rng.random()
        if tier_roll < 0.34:
            tier = PriorityTier.MASS
            day = _weighted_choice(rng, [(1, 50), (2, 30), (3, 12), (4, 8)])
            cutoff = round(rng.uniform(5.5, 6.8), 1)
            duration = rng.choice([10, 10, 15, 15, 20])
            panels = rng.randint(3, 6)
            branch_focus = []  # hires any branch
        elif tier_roll < 0.75:
            tier = PriorityTier.CORE
            day = _weighted_choice(rng, [(1, 25), (2, 35), (3, 30), (4, 10)])
            cutoff = round(rng.uniform(6.8, 7.8), 1)
            duration = rng.choice([20, 20, 25, 30])
            panels = rng.randint(2, 4)
            branch_focus = rng.sample(
                [b for b, _ in BRANCHES_WEIGHTED],
                k=rng.randint(2, 4),
            )
        else:
            tier = PriorityTier.DREAM
            day = _weighted_choice(rng, [(1, 5), (2, 15), (3, 40), (4, 40)])
            cutoff = round(rng.uniform(7.8, 9.0), 1)
            duration = rng.choice([30, 30, 40, 45])
            panels = rng.randint(1, 3)
            branch_focus = []  # dream tech companies usually take CS/IT/ECE broadly
            if rng.random() < 0.5:
                branch_focus = ["CSE", "IT", "ECE"]

        full_day = rng.random() < 0.6
        if full_day:
            w_start, w_end = settings.DAY_START_MIN, settings.DAY_END_MIN
        else:
            half = rng.choice(["morning", "afternoon"])
            if half == "morning":
                w_start, w_end = settings.DAY_START_MIN, settings.DAY_START_MIN + (settings.DAY_END_MIN - settings.DAY_START_MIN) // 2
            else:
                w_start, w_end = settings.DAY_START_MIN + (settings.DAY_END_MIN - settings.DAY_START_MIN) // 2, settings.DAY_END_MIN

        companies.append(GenCompany(
            name=name, day=day, priority_tier=tier, cgpa_cutoff=cutoff,
            interview_duration_min=duration, window_start_min=w_start,
            window_end_min=w_end, num_panels=panels, branch_focus=branch_focus,
        ))
    return companies


def _shortlist_target_size(tier: PriorityTier, rng: random.Random) -> int:
    if tier == PriorityTier.MASS:
        return rng.randint(90, 200)
    if tier == PriorityTier.CORE:
        return rng.randint(35, 100)
    return rng.randint(15, 45)


def generate_shortlists(
    rng: random.Random, companies: list[GenCompany], students: list[GenStudent]
) -> list[list[int]]:
    """Returns, per company index, a list of student indices shortlisted."""
    # Precompute a "desirability" score per student per soft margin so that
    # students well above a company's cutoff are likelier to be shortlisted,
    # and students below it can still sneak in occasionally (real placement
    # cells bend cutoffs for branch quotas / diversity requirements).
    result = []
    for company in companies:
        eligible_pool = []
        for idx, s in enumerate(students):
            if company.branch_focus and s.branch not in company.branch_focus:
                # still a small chance of a cross-branch shortlist (dual degree, etc.)
                if rng.random() > 0.03:
                    continue
            margin = s.cgpa - company.cgpa_cutoff
            if margin < -0.6:
                weight = 0.0
            elif margin < 0:
                weight = 0.15
            else:
                weight = 1.0 + margin  # stronger students weighted higher -> overlapping lists
            if weight > 0:
                eligible_pool.append((idx, weight))

        target = min(_shortlist_target_size(company.priority_tier, rng), len(eligible_pool))
        if target == 0 or not eligible_pool:
            result.append([])
            continue

        idxs = [i for i, _ in eligible_pool]
        weights = [w for _, w in eligible_pool]
        chosen = set()
        # weighted sample without replacement
        pool = list(zip(idxs, weights))
        rng.shuffle(pool)  # break ties fairly before weighted pass
        pool.sort(key=lambda p: rng.random() ** (1.0 / max(p[1], 1e-6)), reverse=True)
        for idx, _ in pool[:target]:
            chosen.add(idx)
        result.append(sorted(chosen))
    return result


def generate_rooms(n: int) -> list[str]:
    return [f"R{str(i).zfill(2)}" for i in range(1, n + 1)]


def generate_dataset(seed: int | None = None):
    rng = random.Random(seed if seed is not None else settings.RANDOM_SEED)
    students = generate_students(rng, settings.NUM_STUDENTS)
    companies = generate_companies(rng, settings.NUM_COMPANIES, settings.NUM_DAYS)
    shortlists = generate_shortlists(rng, companies, students)
    rooms = generate_rooms(settings.NUM_ROOMS)
    return students, companies, shortlists, rooms
