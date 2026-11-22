"""Deterministic clock (section 3.5).

`now()` is UTC and timezone-aware everywhere. Tests freeze it with set_now() or
the frozen_time() context manager; production code never imports datetime.now
directly, which is what makes seed data and demo resets reproducible.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone

_override: datetime | None = None


def now() -> datetime:
    """Current UTC time, or the frozen time while an override is active."""
    if _override is not None:
        return _override
    return datetime.now(timezone.utc)


def set_now(value: datetime) -> None:
    """Freeze the clock at `value`. Naive datetimes are interpreted as UTC."""
    global _override
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    _override = value.astimezone(timezone.utc)


def reset_now() -> None:
    """Clear any override; the clock resumes from the wall clock."""
    global _override
    _override = None


@contextmanager
def frozen_time(value: datetime):
    """Context manager: freeze the clock for the block, restore afterwards."""
    set_now(value)
    try:
        yield now()
    finally:
        reset_now()