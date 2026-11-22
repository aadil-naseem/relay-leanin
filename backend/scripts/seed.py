"""Seed the demo world into the current database (without dropping the schema).

Usage: python scripts/seed.py
For a clean reset (drop + recreate + seed + initial snapshot): reset_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.demo_seed import seed, verify_counts  # noqa: E402


def main() -> int:
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        counts = seed(session)
        session.commit()
        actual = verify_counts(session)
    print("seeded:", counts)
    if actual != counts:
        print(f"ERROR: database counts differ: {actual}")
        return 1
    print("verified:", actual)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
