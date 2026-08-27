"""
Central configuration.

DATABASE_URL drives everything. In docker-compose we point this at the
`mysql` service. For local unit testing (no MySQL server needed) the test
suite overrides this with a SQLite URL — the app code itself never assumes
a specific dialect; it only uses SQLAlchemy Core/ORM features that both
backends support.
"""
import os


class Settings:
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://scheduler:scheduler@localhost:3306/placement_scheduler",
    )

    # ---- Campus / event constants -------------------------------------
    NUM_DAYS: int = int(os.getenv("NUM_DAYS", 4))
    DAY_START_MIN: int = int(os.getenv("DAY_START_MIN", 9 * 60))   # 09:00
    DAY_END_MIN: int = int(os.getenv("DAY_END_MIN", 18 * 60))      # 18:00
    SLOT_GRANULARITY_MIN: int = int(os.getenv("SLOT_GRANULARITY_MIN", 5))
    NUM_ROOMS: int = int(os.getenv("NUM_ROOMS", 20))
    NUM_STUDENTS: int = int(os.getenv("NUM_STUDENTS", 800))
    NUM_COMPANIES: int = int(os.getenv("NUM_COMPANIES", 35))

    # Replan behaviour
    MAX_SPILLOVER_MIN: int = int(os.getenv("MAX_SPILLOVER_MIN", 60))
    # how far past the official day end a delayed company may still run
    # before the coordinator has to accept unscheduled interviews.

    RANDOM_SEED: int = int(os.getenv("RANDOM_SEED", 42))


settings = Settings()

SLOTS_PER_DAY = (
    (settings.DAY_END_MIN - settings.DAY_START_MIN) // settings.SLOT_GRANULARITY_MIN
)
