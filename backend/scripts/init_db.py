"""Creates all tables. No Alembic needed (section 6). Usage: python scripts/init_db.py"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import inspect  # noqa: E402

from app.db import engine, init_db  # noqa: E402


def main() -> int:
    init_db()
    inspector = inspect(engine)
    tables = sorted(inspector.get_table_names())
    print(f"created {len(tables)} tables:")
    for table in tables:
        print(f"  {table}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())