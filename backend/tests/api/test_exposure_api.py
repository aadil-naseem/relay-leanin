"""Phase 7: M4 exposure API (section 8) against the seeded demo world.

Section 9 invariants covered here: #1 (replay alert active for the owner) and
the Phase 7 done-when (owner HIGH or above with readable drivers, Oragadam
lower than Ambattur).
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.core import clock
from app.demo_seed import reset_demo
from app.services import exposure as service

FROZEN = datetime(2026, 11, 14, 9, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    from app.main import create_app

    with clock.frozen_time(FROZEN):
        reset_demo()
        service.reset_weather_ttl()
        with TestClient(create_app()) as test_client:
            yield test_client


# ---------------------------------------------------------------- owner exposure


def test_replay_alert_is_active_for_the_owner(client):
    body = client.get("/api/v1/factories/fac_owner/exposure", params={"mode": "replay"}).json()

    assert body["weather"]["mode"] == "replay"
    assert body["weather"]["source"] == "replay"
    assert body["weather"]["degraded"] is False
    assert body["weather"]["attribution"] == "Weather data by Open-Meteo.com"

    assert body["alert"]["active"] is True  # section 9 invariant 1
    assert body["alert"]["level"] in {"HIGH", "SEVERE"}
    assert body["alert"]["onset_in_hours"] is not None
    assert "fac_owner" in body["alert"]["affected_sites"]
    assert "ven_heat" in body["alert"]["affected_sites"]
    assert body["alert"]["headline"]


def test_owner_is_high_or_above_with_readable_drivers(client):
    body = client.get("/api/v1/factories/fac_owner/exposure", params={"mode": "replay"}).json()
    site = body["site"]
    assert site["site_id"] == "fac_owner"
    assert site["site_risk"] >= 50
    assert site["risk_level"] in {"HIGH", "SEVERE"}
    assert site["drivers"]  # readable, plain-word drivers
    joined = " | ".join(site["drivers"])
    assert "mm forecast" in joined
    assert "not an official flood map" in joined
    assert site["max24_mm"] > 150
    assert site["hazard"] == pytest.approx(1.0)
    assert site["onset_in_hours"] is not None
    assert 20 <= site["onset_in_hours"] <= 40  # the lead the blueprint wants
    assert site["wet_spell_hours"] > 0


def test_oragadam_scores_lower_than_ambattur(client):
    points = client.get("/api/v1/exposure/map", params={"mode": "replay"}).json()["points"]
    by_id = {point["site_id"]: point for point in points}
    assert by_id["fac_oragadam"]["site_risk"] < by_id["fac_owner"]["site_risk"]
    assert by_id["fac_oragadam"]["site_risk"] < by_id["fac_amb_nb"]["site_risk"]
    # the dry inland partners are low risk - the storm is not everywhere
    assert by_id["fac_hosur"]["site_risk"] < 10
    assert by_id["fac_peenya"]["site_risk"] < 10


def test_routes_are_scored_or_honestly_null(client):
    body = client.get("/api/v1/factories/fac_owner/exposure", params={"mode": "replay"}).json()
    assert len(body["routes"]) == 3  # three exits for the Ambattur cluster
    for route in body["routes"]:
        assert route["exit_id"].startswith("exit_")
        if route["route_risk"] is None:
            assert route["low_share"] is None
        else:
            assert 0 <= route["route_risk"] <= 100
    assert body["site"]["isolation"] is False  # at least one exit stays usable


def test_trace_explains_the_numbers(client):
    body = client.get("/api/v1/factories/fac_owner/exposure", params={"mode": "replay"}).json()
    steps = [entry["step"] for entry in body["trace"]]
    assert steps[0] == "weather"
    assert "site_risk" in steps
    assert "routes" in steps
    assert "alert" in steps
    risk_entries = [entry for entry in body["trace"] if entry["step"] == "site_risk"]
    assert len(risk_entries) == 9  # owner + 2 vendors + 6 partners
    assert all("hazard" in entry["detail"] for entry in risk_entries)


def test_exposure_snapshot_is_persisted(client):
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from app.db import engine
    from app.models import ExposureSnapshot

    body = client.get("/api/v1/factories/fac_owner/exposure", params={"mode": "replay"}).json()
    assert body["alert"]["active"] is True
    with Session(engine) as session:
        rows = session.scalars(select(ExposureSnapshot).where(ExposureSnapshot.factory_id == "fac_owner")).all()
        assert rows
        row = rows[-1]
        assert row.mode == "replay"
        assert row.alert is True
        assert row.forecast_hash
        assert "sites" in row.result
        assert len(row.forecast_hash) == 32


# ---------------------------------------------------------------- modes + map


def test_demo_mode_switch_is_honoured_and_persisted(client):
    state = client.get("/api/v1/demo/state").json()
    assert state["weather_mode"] == "replay"
    assert state["data_label"] == "SIMULATED SAMPLE"

    switched = client.post("/api/v1/demo/mode", json={"weather": "synthetic"})
    assert switched.status_code == 200
    assert switched.json()["weather_mode"] == "synthetic"

    # no ?mode -> the stored demo mode wins
    body = client.get("/api/v1/factories/fac_owner/exposure").json()
    assert body["weather"]["mode"] == "synthetic"
    assert body["weather"]["source"] == "synthetic"

    back = client.post("/api/v1/demo/mode", json={"weather": "replay"})
    assert back.json()["weather_mode"] == "replay"


def test_invalid_mode_is_422(client):
    assert client.post("/api/v1/demo/mode", json={"weather": "hurricane"}).status_code == 422
    assert client.get("/api/v1/factories/fac_owner/exposure", params={"mode": "hurricane"}).status_code == 422


def test_map_covers_every_site(client):
    body = client.get("/api/v1/exposure/map", params={"mode": "replay"}).json()
    site_ids = {point["site_id"] for point in body["points"]}
    assert {"fac_owner", "ven_heat", "sup_steel"} <= site_ids
    assert len([site_id for site_id in site_ids if site_id.startswith("fac_")]) == 7
    for point in body["points"]:
        assert point["name"]
        assert point["lat"] != 0.0 and point["lon"] != 0.0
        assert point["risk_level"] in {"LOW", "MODERATE", "HIGH", "SEVERE"}


def test_live_mode_degrades_without_network(client, monkeypatch):
    """In live mode with the network unavailable the ladder must still answer."""
    import httpx

    def _boom(*_args, **_kwargs):
        raise httpx.ConnectError("no network in tests")

    monkeypatch.setattr("app.adapters.weather._fetch_live", _boom)
    service.reset_weather_ttl()

    body = client.get("/api/v1/factories/fac_owner/exposure", params={"mode": "live"}).json()
    assert body["weather"]["mode"] == "live"
    assert body["weather"]["source"] == "replay"
    assert body["weather"]["degraded"] is True
    assert body["alert"]["active"] is True  # the demo still works


def test_unknown_factory_is_404(client):
    response = client.get("/api/v1/factories/fac_nope/exposure")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"