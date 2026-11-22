"""Demo world seeder (blueprint section 9, Phase 3).

Reads `backend/data/seed/*.json`, converts relative times (`due_in_days`,
`last_confirmed_days_ago`) to absolute dates against the current clock, and
loads everything with `is_sample = True` (R9). `reset_demo()` drops and
recreates the schema, seeds, and writes the initial readiness snapshot row so
the demo has a clean, reproducible state - `POST /demo/reset` (Phase 13) calls
this same function.

The clock comes from app.core.clock, so tests freezing the clock get dates
relative to the frozen time - data never goes stale relative to "now".
"""

from __future__ import annotations

import json
import logging
from datetime import timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import now
from app.core.locks import DEMO_WRITE_LOCK
from app.db import Base, engine
from app.enums import (
    BackupStatus,
    CheckKey,
    ProcessCode,
    Role,
    VendorKind,
)
from app.models import (
    AppState,
    BackupRelationship,
    Factory,
    HazardZone,
    Machine,
    Order,
    Part,
    PartStep,
    Passport,
    PassportShare,
    ReadinessSnapshot,
    RelationshipCheck,
    Rfq,
    Route,
    SiteTerrain,
    Vendor,
    VendorLink,
)

logger = logging.getLogger(__name__)

SEED_DIR = Path(__file__).resolve().parents[1] / "data" / "seed"
CACHE_DIR = Path(__file__).resolve().parents[1] / "data" / "cache"
SEED_VERSION = 1
INITIAL_SNAPSHOT_ID = "rdy_initial"

_FILES = ("factories", "vendors", "machines", "parts", "orders", "relationships")

EXPECTED_COUNTS = {
    "factories": 7,  # 1 owner + 6 partners
    "vendors": 2,  # 1 vendor + 1 supplier
    "vendor_links": 2,
    "machines": 33,
    "parts": 6,
    "part_steps": 12,
    "orders": 8,
    "relationships": 6,
    "relationship_checks": 30,
}


def _load(name: str) -> dict[str, Any]:
    with (SEED_DIR / f"{name}.json").open(encoding="utf-8") as handle:
        return json.load(handle)


def load_seed_data() -> dict[str, Any]:
    """Read and sanity-check all seed files (fail fast on wrong shape)."""
    data = {name: _load(name) for name in _FILES}
    total = len(data["factories"]["factories"])
    partners = [f for f in data["factories"]["factories"] if f["role"] == "PARTNER"]
    if not total or not partners:
        raise ValueError("seed factories.json must contain an owner and partners")
    return data


def _wipe(session: Session) -> None:
    """Delete seed-managed rows (FK-safe) so seed() can run repeatedly.

    Prefetch data (hazard_zones, site_terrain, routes) and runtime tables
    (exposure, stress, recovery) are NOT touched - only reset_demo() rebuilds
    the whole schema.
    """
    from sqlalchemy import delete

    for table in (
        RelationshipCheck,
        BackupRelationship,
        PassportShare,
        Rfq,
        Passport,
        Order,
        PartStep,
        Part,
        Machine,
        VendorLink,
        Vendor,
        Factory,
    ):
        session.execute(delete(table))
    session.execute(delete(AppState).where(AppState.key == "demo"))


def _seed(session: Session) -> dict[str, int]:
    data = load_seed_data()
    _wipe(session)
    current = now()

    factories: dict[str, Factory] = {}
    for row in data["factories"]["factories"]:
        factory = Factory(
            id=row["id"],
            role=Role(row["role"]),
            name=row["name"],
            is_sample=True,
            lat=row["lat"],
            lon=row["lon"],
            cluster_id=row["cluster_id"],
            hazard_zone_id=row.get("hazard_zone_id"),
            grid_id=row.get("grid_id"),
            shift_hours_per_day=row.get("shift_hours_per_day", 16.0),
            materials_handled=row.get("materials_handled", []),
            typical_lead_time_hours=row.get("typical_lead_time_hours"),
            mobilisation_hours=row.get("mobilisation_hours"),
            spare_hours_per_week=row.get("spare_hours_per_week", {}),
            contacts=row.get("contacts", []),
        )
        factories[factory.id] = factory
    session.add_all(factories.values())

    vendors: dict[str, Vendor] = {}
    for row in data["vendors"]["vendors"]:
        vendor = Vendor(
            id=row["id"],
            kind=VendorKind(row["kind"]),
            name=row["name"],
            is_sample=True,
            lat=row["lat"],
            lon=row["lon"],
            cluster_id=row["cluster_id"],
            hazard_zone_id=row.get("hazard_zone_id"),
            grid_id=row.get("grid_id"),
            process=ProcessCode(row["process"]) if row.get("process") else None,
            material=row.get("material"),
            turnaround_hours=row.get("turnaround_hours", 24.0),
        )
        vendors[vendor.id] = vendor
    session.add_all(vendors.values())
    session.add_all(
        VendorLink(factory_id=link["factory_id"], vendor_id=link["vendor_id"])
        for link in data["vendors"]["vendor_links"]
    )

    for row in data["machines"]["machines"]:
        session.add(
            Machine(
                id=row["id"],
                factory_id=row["factory_id"],
                process=ProcessCode(row["process"]),
                name=row["name"],
                achievable_tolerance_mm=row.get("achievable_tolerance_mm"),
                envelope_mm=row.get("envelope_mm"),
            )
        )

    for row in data["parts"]["parts"]:
        part = Part(
            id=row["id"],
            factory_id=row["factory_id"],
            name=row["name"],
            drawing_no=row.get("drawing_no"),
            customer_alias=row.get("customer_alias"),
            material=row["material"],
            is_critical=row.get("is_critical", False),
            typical_batch_qty=row.get("typical_batch_qty", 1),
        )
        session.add(part)
        for step in row["steps"]:
            session.add(
                PartStep(
                    id=f"st_{row['id']}_{step['seq']}",
                    part_id=part.id,
                    seq=step["seq"],
                    process=ProcessCode(step["process"]),
                    hours_per_unit=step.get("hours_per_unit", 0.0),
                    setup_hours=step.get("setup_hours", 0.0),
                    tolerance_mm=step.get("tolerance_mm"),
                    outsourced=step.get("outsourced", False),
                )
            )

    for row in data["orders"]["orders"]:
        session.add(
            Order(
                id=row["id"],
                factory_id="fac_owner",
                part_id=row["part_id"],
                qty=row["qty"],
                due_at=current + timedelta(days=row["due_in_days"]),
                value_inr=row["value_inr"],
                customer_alias=row.get("customer_alias"),
            )
        )

    for row in data["relationships"]["relationships"]:
        confirmed = (
            current - timedelta(days=row["last_confirmed_days_ago"])
            if row.get("last_confirmed_days_ago") is not None
            else None
        )
        relationship = BackupRelationship(
            id=row["id"],
            owner_id=row["owner_id"],
            partner_id=row["partner_id"],
            status=BackupStatus(row["status"]),
            last_confirmed_at=confirmed,
            customer_approval_required=row.get("customer_approval_required", True),
            notes=row.get("notes"),
        )
        session.add(relationship)
        for check in row["checks"]:
            done = bool(check["done"])
            session.add(
                RelationshipCheck(
                    id=f"chk_{row['id']}_{check['key']}",
                    relationship_id=relationship.id,
                    key=CheckKey(check["key"]),
                    done=done,
                    done_at=current if done else None,
                )
            )

    session.add(AppState(key="demo", value={"seed_version": SEED_VERSION}))
    session.flush()

    counts = {
        "factories": len(factories),
        "vendors": len(vendors),
        "vendor_links": len(data["vendors"]["vendor_links"]),
        "machines": len(data["machines"]["machines"]),
        "parts": len(data["parts"]["parts"]),
        "part_steps": sum(len(p["steps"]) for p in data["parts"]["parts"]),
        "orders": len(data["orders"]["orders"]),
        "relationships": len(data["relationships"]["relationships"]),
        "relationship_checks": sum(len(r["checks"]) for r in data["relationships"]["relationships"]),
    }
    for table, expected in EXPECTED_COUNTS.items():
        if counts[table] != expected:
            raise ValueError(f"seed count mismatch for {table}: {counts[table]} != {expected}")
    return counts


def load_exposure_cache(session: Session) -> dict[str, int]:
    """Load committed prefetch JSON (Phase 4) into hazard_zones, site_terrain, routes.

    Reads data/cache/zones.json, terrain.json and routes.json if present and
    returns the row counts. Missing files are fine (fresh clone mid-build);
    the Phase 4 done-when is that the cache is committed so a fresh clone has
    them. Zone membership in site_terrain.zone_ids is derived here with the
    circle test; factory zone membership itself stays on factories.hazard_zone_id
    (pinned in Phase 2).
    """
    from app.core.geo import point_in_circle

    counts = {"hazard_zones": 0, "site_terrain": 0, "routes": 0}

    zones_path = CACHE_DIR / "zones.json"
    if zones_path.exists():
        zones_payload = json.loads(zones_path.read_text(encoding="utf-8"))
        for row in zones_payload["zones"]:
            session.add(
                HazardZone(
                    id=row["id"],
                    name=row["name"],
                    center_lat=row["center_lat"],
                    center_lon=row["center_lon"],
                    radius_m=row["radius_m"],
                    note=row["note"],
                )
            )
            counts["hazard_zones"] += 1

    terrain_path = CACHE_DIR / "terrain.json"
    if terrain_path.exists():
        terrain_payload = json.loads(terrain_path.read_text(encoding="utf-8"))
        all_zones = session.scalars(select(HazardZone)).all()
        for site_id, site in terrain_payload["sites"].items():
            zone_ids = [
                zone.id
                for zone in all_zones
                if point_in_circle(site["lat"], site["lon"], zone.center_lat, zone.center_lon, zone.radius_m)
            ]
            session.add(
                SiteTerrain(
                    site_id=site_id,
                    elevation_m=site["elevation_m"],
                    ring_mean_m=site["ring_mean_m"],
                    relative_m=site["relative_m"],
                    nearest_water_m=site.get("nearest_water_m"),
                    zone_ids=zone_ids,
                    source=terrain_payload.get("source", "open-meteo-elevation"),
                )
            )
            counts["site_terrain"] += 1

    routes_path = CACHE_DIR / "routes.json"
    if routes_path.exists():
        routes_payload = json.loads(routes_path.read_text(encoding="utf-8"))
        for row in routes_payload["routes"]:
            session.add(
                Route(
                    id=row["route_id"],
                    site_id=row["site_id"],
                    exit_id=row["exit_id"],
                    length_km=row["length_km"],
                    samples=row["samples"],
                    low_share=row.get("low_share"),
                    underpass_count=row.get("underpass_count", 0),
                )
            )
            counts["routes"] += 1

    session.flush()
    return counts


def seed(session: Session) -> dict[str, int]:
    """Seed into the existing (empty or wipeable) schema."""
    return _seed(session)


def reset_demo() -> dict[str, int]:
    """Rebuild the demo world atomically: wipe every row, reseed, reload cache.

    The rebuild deletes rows instead of dropping tables. Dropping and recreating
    the schema is not atomic on pysqlite (the driver commits around DDL), which
    left a window where a concurrent request saw "no such table" and returned a
    500 without CORS headers. Row deletes and inserts run in one transaction, so
    readers in WAL mode keep serving the previous committed world until this
    commits. `DEMO_WRITE_LOCK` serializes the rebuild against other demo writes
    and stops two resets overlapping.

    Used by `scripts/reset_demo.py` and by `POST /demo/reset`.
    """
    logger.info("resetting demo world (wipe rows + reseed + exposure cache)")
    with DEMO_WRITE_LOCK:
        Base.metadata.create_all(bind=engine)  # no-op when the schema exists
        with Session(engine) as session:
            connection = session.connection()
            for table in reversed(Base.metadata.sorted_tables):
                connection.execute(table.delete())
            counts = _seed(session)
            exposure = load_exposure_cache(session)
            counts.update(exposure)
            session.add(
                ReadinessSnapshot(
                    id=INITIAL_SNAPSHOT_ID,
                    factory_id="fac_owner",
                    window_hours=48,
                    score=0.0,
                    weighted_score=0.0,
                    breakdown={},
                    reason="INITIAL (not yet computed)",
                )
            )
            session.commit()
    return counts


def verify_counts(session: Session, include_exposure: bool = False) -> dict[str, int]:
    """Row counts straight from the database, for tests and the done-when check."""
    counts = {
        "factories": len(session.scalars(select(Factory)).all()),
        "vendors": len(session.scalars(select(Vendor)).all()),
        "vendor_links": len(session.scalars(select(VendorLink)).all()),
        "machines": len(session.scalars(select(Machine)).all()),
        "parts": len(session.scalars(select(Part)).all()),
        "part_steps": len(session.scalars(select(PartStep)).all()),
        "orders": len(session.scalars(select(Order)).all()),
        "relationships": len(session.scalars(select(BackupRelationship)).all()),
        "relationship_checks": len(session.scalars(select(RelationshipCheck)).all()),
    }
    if include_exposure:
        counts.update(
            {
                "hazard_zones": len(session.scalars(select(HazardZone)).all()),
                "site_terrain": len(session.scalars(select(SiteTerrain)).all()),
                "routes": len(session.scalars(select(Route)).all()),
            }
        )
    return counts


__all__ = [
    "EXPECTED_COUNTS",
    "INITIAL_SNAPSHOT_ID",
    "SEED_DIR",
    "SEED_VERSION",
    "load_exposure_cache",
    "load_seed_data",
    "reset_demo",
    "seed",
    "verify_counts",
]
