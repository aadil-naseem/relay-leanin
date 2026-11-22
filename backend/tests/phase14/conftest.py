"""Shared Phase 14 client with a deterministic replay seed and frozen clock."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.core import clock
from app.demo_seed import reset_demo
from app.services import exposure

FROZEN = datetime(2026, 11, 14, 9, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def phase14_client():
    from app.main import create_app

    with clock.frozen_time(FROZEN):
        reset_demo()
        exposure.reset_weather_ttl()
        with TestClient(create_app()) as test_client:
            yield test_client
