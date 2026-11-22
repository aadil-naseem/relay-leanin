"""Seed the sample world only when the database is empty.

Safe to run on every boot. A fresh clone, a wiped container or a brand-new
host gets the full sample world; an existing database is left untouched, so a
mounted persistent disk keeps its readiness history and demo state.

Used as the first half of the hosted start command; see docs/DEPLOY.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.models import Factory  # noqa: E402


def main() -> int:
    Base.metadata.create_all(bind=engine)  # no-op when the schema exists

    with Session(engine) as session:
        existing = session.scalars(select(Factory)).first()

    if existing is not None:
        print("demo world already present; leaving it untouched")
        return 0

    from app.demo_seed import reset_demo

    counts = reset_demo()
    print(f"seeded demo world: {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
