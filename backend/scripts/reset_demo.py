"""One-command demo reset: drop schema, recreate, seed, initial snapshot.

Usage: python scripts/reset_demo.py
Done-when (Phase 3): runs in < 3 s and produces the section 9 entities.
This is also what POST /demo/reset calls (Phase 13).
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session  # noqa: E402

from app.db import engine  # noqa: E402
from app.demo_seed import reset_demo, verify_counts  # noqa: E402


def main() -> int:
    started = time.perf_counter()
    counts = reset_demo()
    elapsed = time.perf_counter() - started
    with Session(engine) as session:
        actual = verify_counts(session, include_exposure=True)
    ok = actual == counts
    print(f"reset in {elapsed:.2f}s -> {counts}")
    if not ok:
        print(f"ERROR: database counts differ: {actual}")
        return 1
    if elapsed >= 3.0:
        print("ERROR: reset took longer than the 3 s done-when budget")
        return 1
    print("done-when: reset < 3 s - PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
