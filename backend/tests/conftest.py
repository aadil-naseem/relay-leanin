"""Shared pytest setup.

- Puts the backend dir on sys.path so `import app` works from any CWD.
- Points DATABASE_URL at an isolated SQLite file on E: BEFORE app.settings is
  imported (pydantic-settings gives real env vars precedence over .env).
- Resets the frozen clock around every test.
- Deletes the test database at session start and end.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

TEST_DB = BACKEND_DIR / "data" / "test_fcd.sqlite"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core import clock  # noqa: E402


def _delete_test_db() -> None:
    from app.db import engine

    engine.dispose()
    for suffix in ("", "-wal", "-shm"):
        path = Path(str(TEST_DB) + suffix)
        if path.exists():
            try:
                path.unlink()
            except PermissionError:
                pass  # reported as a warning at most; never mask test results


def pytest_sessionstart(session: pytest.Session) -> None:
    _delete_test_db()


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    _delete_test_db()


@pytest.fixture(autouse=True)
def _fresh_clock():
    clock.reset_now()
    yield
    clock.reset_now()


@pytest.fixture()
def client():
    from app.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client