"""Phase 4: prefetch cache tests (NO network - these only read committed files
and the local test database). The prefetch scripts themselves were run once;
their output lives in backend/data/cache/ and is committed.

Covers the Phase 4 task list: JSON schema checks, every site has terrain,
routes have >= 10 samples, replay series length = 72 h, and the seeder loads
the cache into hazard_zones / site_terrain / routes.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config_loader import load_configs
from app.core import clock
from app.db import Base, engine
from app.demo_seed import load_exposure_cache, reset_demo
from app.models import HazardZone, Route, SiteTerrain

BACKEND_DIR = Path(__file__).resolve().parents[2]
CACHE_DIR = BACKEND_DIR / "data" / "cache"


def _load(name: str) -> dict:
    path = CACHE_DIR / f"{name}.json"
    assert path.exists(), f"{name} must be committed for a fresh clone to work offline"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def bundle():
    return load_configs()


@pytest.fixture(scope="module")
def terrain():
    return _load("terrain")


@pytest.fixture(scope="module")
def zones():
    return _load("zones")


@pytest.fixture(scope="module")
def replay():
    return _load("replay_michaung")


@pytest.fixture(scope="module")
def synthetic():
    return _load("synthetic_storm")


# ---------------------------------------------------------------- terrain.json


def test_every_configured_site_has_terrain(bundle, terrain):
    expected = {s.id for s in bundle.cluster.sites}
    expected |= {s.id for s in bundle.cluster.backtest_flooded}
    expected |= {s.id for s in bundle.cluster.backtest_not_flooded}
    assert set(terrain["sites"]) == expected


def test_terrain_facts_are_coherent(terrain):
    for site_id, site in terrain["sites"].items():
        assert site["elevation_m"] > 0, site_id
        assert site["ring_mean_m"] > 0, site_id
        assert site["relative_m"] == pytest.approx(
            site["elevation_m"] - site["ring_mean_m"], abs=0.05
        ), site_id
        assert isinstance(site["nearest_water_m"], (float, int)) or site["nearest_water_m"] is None


def test_low_threshold_is_a_plausible_cluster_floor(terrain):
    low = terrain["low_threshold_m"]
    chennai = [s for s in terrain["sites"].values() if s["elevation_m"] < 100]
    elevations = [s["elevation_m"] for s in chennai]
    assert 0 < low <= max(elevations)  # a 25th-percentile-style floor, not an outlier
    assert terrain["grid_bbox"]["lat_min"] < terrain["grid_bbox"]["lat_max"]


def test_owner_is_in_a_depression_and_oragadam_is_high(terrain):
    """Story-supporting facts: owner sits below its surroundings; the hero
    backup (Oragadam) is on the elevated SIPCOT plateau."""
    owner = terrain["sites"]["fac_owner"]
    oragadam = terrain["sites"]["fac_oragadam"]
    assert owner["relative_m"] < -2.0
    assert oragadam["elevation_m"] > 40.0


# ---------------------------------------------------------------- zones.json


def test_zones_reference_cluster_yaml_zone_ids(bundle, zones):
    zone_ids = {z["id"] for z in zones["zones"]}
    referenced = {s.hazard_zone_id for s in bundle.cluster.sites if s.hazard_zone_id}
    assert referenced <= zone_ids  # every site's zone exists in zones.json


def test_zones_are_circles_with_citations(zones):
    for zone in zones["zones"]:
        assert zone["radius_m"] > 0
        assert 8.0 < zone["center_lat"] < 37.0  # inside India
        assert 68.0 < zone["center_lon"] < 97.0
        # R9: the note must cite public reporting, not sound like an official map
        assert len(zone["note"]) > 80
        assert "illustrative" in json.dumps(zones).lower()
        assert "not official flood maps" in json.dumps(zones).lower()


# ---------------------------------------------------------------- replay


def test_replay_series_shape(bundle, replay):
    assert replay["series_hours"] == 72
    assert replay["series_start_utc"] == "2023-12-03T00:00:00Z"
    expected_sites = {s.id for s in bundle.cluster.sites}
    expected_sites |= {s.id for s in bundle.cluster.backtest_flooded}
    expected_sites |= {s.id for s in bundle.cluster.backtest_not_flooded}
    assert set(replay["sites"]) == expected_sites
    for site_id, series in replay["sites"].items():
        assert len(series["time"]) == 72, site_id
        assert len(series["precipitation_mm"]) == 72, site_id
        assert all(v >= 0.0 for v in series["precipitation_mm"]), site_id


def test_replay_first_hour_aligns_with_series_start(replay):
    first = datetime.fromisoformat(replay["sites"]["fac_owner"]["time"][0]).replace(tzinfo=timezone.utc)
    assert first == datetime(2023, 12, 3, 0, 0, tzinfo=timezone.utc)
    last = datetime.fromisoformat(replay["sites"]["fac_owner"]["time"][-1]).replace(tzinfo=timezone.utc)
    assert last - first == timedelta(hours=71)


def test_replay_owner_matches_the_verified_reference(replay):
    """Phase 0 verified 238.7 mm at Ambattur on 2023-12-04 (archive)."""
    owner = replay["sites"]["fac_owner"]["precipitation_mm"]
    dec4 = sum(owner[24:48])
    assert dec4 == pytest.approx(238.7, abs=1.0)
    assert max(owner) >= 15.0  # a real storm, not a smooth drizzle
    assert sum(owner) >= 250.0


def test_replay_flooded_backtest_sites_got_heavy_rain(replay):
    for site_id in ("bt_ambattur_north", "bt_villivakkam", "bt_thirumudivakkam", "bt_perungudi"):
        assert replay["sites"][site_id]["total_mm"] >= 150.0, site_id


def test_synthetic_storm_is_labelled_and_complete(synthetic):
    assert synthetic["source"] == "synthetic"
    assert "SYNTHETIC" in synthetic["label"]
    assert synthetic["series_hours"] == 72
    profile = synthetic["sites"]["fac_owner"]["precipitation_mm"]
    assert len(profile) == 72
    assert max(profile) > 0 and sum(profile) > 0


# ---------------------------------------------------------------- routes.json


@pytest.fixture(scope="module")
def routes():
    return _load("routes")


def test_routes_have_enough_samples(routes):
    assert routes["routes"], "route prefetch must have produced routes"
    for route in routes["routes"]:
        assert len(route["samples"]) >= 10, route["route_id"]
        assert route["length_km"] > 0, route["route_id"]
        for sample in route["samples"]:
            assert "elevation_m" in sample, route["route_id"]


def test_route_low_share_in_range(routes):
    for route in routes["routes"]:
        assert route["low_share"] is None or 0.0 <= route["low_share"] <= 1.0, route["route_id"]
        assert route["underpass_count"] >= 0


def test_route_sites_have_exits_in_config(bundle, routes):
    route_site_ids = {r["site_id"] for r in routes["routes"]}
    for site_id in route_site_ids:
        site = next(s for s in bundle.cluster.sites if s.id == site_id)
        assert site.cluster_id in bundle.cluster.exits


# ---------------------------------------------------------------- loader into DB


@pytest.fixture(autouse=True)
def _tables():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_loader_loads_cache_into_tables(bundle, terrain, zones, routes):
    frozen = datetime(2026, 11, 14, 9, 0, 0, tzinfo=timezone.utc)
    with clock.frozen_time(frozen):
        with Session(engine) as session:
            counts = load_exposure_cache(session)
            session.commit()
    assert counts["hazard_zones"] == len(zones["zones"])
    assert counts["site_terrain"] == len(terrain["sites"])
    assert counts["routes"] == len(routes["routes"])

    with Session(engine) as session:
        # zone membership derived by circle test
        owner_terrain = session.get(SiteTerrain, "fac_owner")
        assert "zone_ambattur_north" in owner_terrain.zone_ids
        oragadam_terrain = session.get(SiteTerrain, "fac_oragadam")
        assert oragadam_terrain.zone_ids == []  # outside every curated circle
        # routes table round trip
        route = session.scalars(select(Route).where(Route.site_id == "fac_owner")).first()
        assert route is not None
        assert len(route.samples) >= 10
        assert route.underpass_count >= 0
        # zones table
        zone = session.get(HazardZone, "zone_ambattur_north")
        assert zone.radius_m > 0
        assert "2023" in zone.note  # cites the Michaung reporting


def test_reset_demo_loads_exposure_cache():
    with clock.frozen_time(datetime(2026, 11, 14, 9, 0, 0, tzinfo=timezone.utc)):
        counts = reset_demo()
    assert counts["hazard_zones"] >= 1
    assert counts["site_terrain"] >= 16
    assert counts["routes"] >= 1
