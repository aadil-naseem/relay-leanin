"""Phase 14 failure-injection checks for offline weather, reset and uploads."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest
from sqlalchemy.orm import Session

from app.adapters import weather
from app.core import clock
from app.db import engine
from app.demo_seed import reset_demo
from app.services import exposure as exposure_service

FROZEN = datetime(2026, 11, 14, 9, 0, 0, tzinfo=timezone.utc)
TEST_DB = Path(__file__).resolve().parents[2] / "data" / "test_fcd.sqlite"


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    from app.main import create_app

    with clock.frozen_time(FROZEN):
        reset_demo()
        exposure_service.reset_weather_ttl()
        with TestClient(create_app()) as test_client:
            yield test_client


def test_live_forecast_failures_degrade_to_cache_then_replay(client, monkeypatch):
    def valid_live(sites):
        return {site.site_id: tuple([0.1] * 72) for site in sites}

    monkeypatch.setattr(weather, "_fetch_live", valid_live)
    exposure_service.reset_weather_ttl()
    live = client.get("/api/v1/factories/fac_owner/exposure", params={"mode": "live"})
    assert live.status_code == 200, live.text
    assert live.json()["weather"]["source"] == "live"
    assert live.json()["weather"]["degraded"] is False

    def service_unavailable(_sites):
        raise httpx.HTTPStatusError(
            "injected Open-Meteo 500",
            request=httpx.Request("GET", weather.FORECAST_URL),
            response=httpx.Response(500),
        )

    monkeypatch.setattr(weather, "_fetch_live", service_unavailable)
    exposure_service.reset_weather_ttl()
    cached = client.get("/api/v1/factories/fac_owner/exposure", params={"mode": "live"})
    assert cached.status_code == 200, cached.text
    assert cached.json()["weather"]["source"] == "cache"
    assert cached.json()["weather"]["degraded"] is True

    with Session(engine) as session:
        weather.clear_forecast_cache(session)
    exposure_service.reset_weather_ttl()

    def timeout(_sites):
        raise httpx.ReadTimeout("injected forecast timeout")

    monkeypatch.setattr(weather, "_fetch_live", timeout)
    replay = client.get("/api/v1/factories/fac_owner/exposure", params={"mode": "live"})
    assert replay.status_code == 200, replay.text
    assert replay.json()["weather"]["source"] == "replay"
    assert replay.json()["weather"]["degraded"] is True


def test_deleted_database_is_rebuilt_by_demo_reset(client):
    engine.dispose()
    for suffix in ("", "-wal", "-shm"):
        path = Path(f"{TEST_DB}{suffix}")
        if path.exists():
            path.unlink()

    reset = client.post("/api/v1/demo/reset")
    assert reset.status_code == 200, reset.text
    health = client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.json()["db"] == "ok"
    dashboard = client.get("/api/v1/dashboard/fac_owner")
    assert dashboard.status_code == 200, dashboard.text
    assert dashboard.json()["alert"]["active"] is True


def test_empty_and_malformed_uploads_are_422_not_500(client):
    empty = client.post(
        "/api/v1/passports/extract",
        files={"file": ("empty.png", b"", "image/png")},
    )
    assert empty.status_code == 422, empty.text

    malformed = client.post(
        "/api/v1/passports/extract",
        files={"file": ("broken.png", b"not a valid PNG or PDF", "image/png")},
    )
    assert malformed.status_code == 422, malformed.text
    assert malformed.json()["error"]["code"] == "INVALID_DOCUMENT"
