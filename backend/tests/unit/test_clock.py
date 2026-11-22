"""Phase 1: deterministic clock behaviour (section 3.5)."""

from datetime import datetime, timezone

from app.core import clock


def test_now_is_utc_and_aware():
    value = clock.now()
    assert value.tzinfo is not None
    drift_seconds = abs((datetime.now(timezone.utc) - value).total_seconds())
    assert drift_seconds < 5.0


def test_set_now_freezes_and_reset_now_restores():
    frozen = datetime(2026, 11, 14, 6, 0, 0, tzinfo=timezone.utc)
    clock.set_now(frozen)
    assert clock.now() == frozen
    clock.reset_now()
    assert clock.now() != frozen


def test_frozen_time_context_manager_restores_clock():
    frozen = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    with clock.frozen_time(frozen) as seen:
        assert seen == frozen
        assert clock.now() == frozen
    assert clock.now() != frozen


def test_naive_override_is_treated_as_utc():
    naive = datetime(2026, 3, 1, 12, 0, 0)
    clock.set_now(naive)
    assert clock.now().tzinfo == timezone.utc
    assert clock.now().hour == 12
    clock.reset_now()