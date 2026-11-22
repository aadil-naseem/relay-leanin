"""Phase 2: the whole schema builds, and values survive a write -> read round trip."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.core import clock
from app.db import Base, engine
from app.enums import (
    BackupStatus,
    CheckKey,
    PassportStatus,
    ProcessCode,
    Role,
    ShareLevel,
    Trigger,
    VendorKind,
)
from app.models import (
    AppState,
    BackupRelationship,
    ExposureSnapshot,
    Factory,
    ForecastCache,
    HazardZone,
    Machine,
    Order,
    Part,
    PartStep,
    Passport,
    PassportShare,
    ReadinessSnapshot,
    RecoveryRequest,
    RecoveryStep,
    RelationshipCheck,
    Rfq,
    Route,
    SiteTerrain,
    StressTest,
    Vendor,
    VendorLink,
)

EXPECTED_TABLES = {
    "app_state", "backup_relationships", "exposure_snapshots", "factories", "forecast_cache",
    "hazard_zones", "machines", "orders", "passport_shares", "passports", "parts", "part_steps",
    "readiness_snapshots", "recovery_requests", "recovery_steps", "relationship_checks", "rfqs",
    "routes", "site_terrain", "stress_tests", "vendors", "vendor_links",
}


@pytest.fixture(autouse=True)
def _tables():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_all_22_tables_exist():
    inspector = inspect(engine)
    assert set(inspector.get_table_names()) == EXPECTED_TABLES


def test_factory_aggregate_round_trip():
    frozen = datetime(2026, 11, 14, 9, 0, 0, tzinfo=timezone.utc)
    with clock.frozen_time(frozen):
        with Session(engine) as session:
            factory = Factory(
                id="fac_owner",
                role=Role.OWNER,
                name="Sample Precision Components",
                lat=13.100,
                lon=80.155,
                cluster_id="cl_ambattur",
                hazard_zone_id="zone_ambattur_north",
                grid_id="grid_chennai_metro",
                materials_handled=["EN24", "EN8"],
                spare_hours_per_week={"TURN": 40.0},
                contacts=["owner", "production"],
            )
            machine = Machine(
                id="mch_lathe_1", factory_id="fac_owner", process=ProcessCode.TURN,
                name="Lathe 1", achievable_tolerance_mm=0.02, envelope_mm=400.0,
            )
            vendor = Vendor(
                id="ven_heat", kind=VendorKind.VENDOR, name="Sample Heat Treat Works",
                lat=13.105, lon=80.150, cluster_id="cl_ambattur",
                process=ProcessCode.HEAT_TREAT, turnaround_hours=24.0,
            )
            link = VendorLink(factory_id="fac_owner", vendor_id="ven_heat")
            session.add_all([factory, machine, vendor, link])
            session.commit()

            loaded = session.get(Factory, "fac_owner")
            assert loaded is not None
            assert loaded.role == Role.OWNER
            assert loaded.materials_handled == ["EN24", "EN8"]
            assert loaded.spare_hours_per_week == {"TURN": 40.0}
            assert loaded.created_at == frozen  # aware UTC survives the round trip
            assert len(loaded.machines) == 1
            assert loaded.machines[0].process == ProcessCode.TURN
            assert [link.vendor.name for link in loaded.vendor_links] == ["Sample Heat Treat Works"]


def test_part_route_and_order_round_trip():
    due = datetime(2026, 11, 20, 12, 0, 0, tzinfo=timezone.utc)
    with Session(engine) as session:
        session.add(Factory(id="fac_owner", role=Role.OWNER, name="F", lat=13.1, lon=80.155, cluster_id="c"))
        session.add(Passport(id="pas_1", status=PassportStatus.DRAFT))
        session.commit()  # passports.part_id <-> parts.passport_id is a use_alter cycle:
        # insert the passport before anything references it.

        part = Part(
            id="prt_a", factory_id="fac_owner", name="Hydraulic piston rod", material="EN24",
            is_critical=True, typical_batch_qty=50, passport_id="pas_1",
        )
        steps = [
            PartStep(id="st_1", part_id="prt_a", seq=1, process=ProcessCode.TURN, hours_per_unit=0.10, setup_hours=1.0),
            PartStep(id="st_2", part_id="prt_a", seq=2, process=ProcessCode.HEAT_TREAT, outsourced=True),
            PartStep(id="st_3", part_id="prt_a", seq=3, process=ProcessCode.GRIND_CYL, hours_per_unit=0.12, tolerance_mm=0.005),
        ]
        order = Order(
            id="ord_107", factory_id="fac_owner", part_id="prt_a",
            qty=50, due_at=due, value_inr=1_200_000.0, customer_alias="ACME (SAMPLE)",
        )
        session.add_all([part, *steps, order])
        session.commit()

        loaded_order = session.get(Order, "ord_107")
        assert loaded_order.due_at == due
        assert loaded_order.value_inr == 1_200_000.0
        steps_loaded = loaded_order.part.steps
        assert [step.seq for step in steps_loaded] == [1, 2, 3]
        assert steps_loaded[1].outsourced is True
        assert steps_loaded[2].tolerance_mm == 0.005


def test_relationship_checks_round_trip():
    confirmed = datetime(2026, 8, 6, 0, 0, 0, tzinfo=timezone.utc)
    with clock.frozen_time(confirmed):
        with Session(engine) as session:
            session.add_all([
                Factory(id="fac_owner", role=Role.OWNER, name="F", lat=13.1, lon=80.155, cluster_id="c"),
                Factory(id="fac_oragadam", role=Role.PARTNER, name="O", lat=12.842, lon=79.952, cluster_id="co"),
            ])
            relationship = BackupRelationship(
                id="rel_1", owner_id="fac_owner", partner_id="fac_oragadam",
                status=BackupStatus.READY, last_confirmed_at=confirmed,
            )
            checks = [
                RelationshipCheck(id=f"chk_{key.value}", relationship_id="rel_1", key=key, done=True, done_at=confirmed)
                for key in CheckKey
            ]
            session.add_all([relationship, *checks])
            session.commit()

            loaded = session.get(BackupRelationship, "rel_1")
            assert loaded.status == BackupStatus.READY
            assert loaded.last_confirmed_at == confirmed
            assert {check.key for check in loaded.checks} == set(CheckKey)
            assert all(check.done for check in loaded.checks)


def test_computed_payload_tables_round_trip():
    computed = datetime(2026, 11, 14, 9, 0, 0, tzinfo=timezone.utc)
    with clock.frozen_time(computed):
        with Session(engine) as session:
            session.add_all([
                Factory(id="fac_owner", role=Role.OWNER, name="F", lat=13.1, lon=80.155, cluster_id="c"),
                Factory(id="fac_oragadam", role=Role.PARTNER, name="O", lat=12.842, lon=79.952, cluster_id="co"),
            ])
            session.commit()
            session.add_all([
                ForecastCache(key="f1", payload={"hours": [1.0, 2.0]}, source="replay"),
                HazardZone(id="zone_a", name="Ambattur north", center_lat=13.102, center_lon=80.152, radius_m=4000),
                SiteTerrain(
                    site_id="fac_owner", elevation_m=9.0, ring_mean_m=12.4, relative_m=-3.4,
                    nearest_water_m=380.0, zone_ids=["zone_ambattur_north"],
                ),
                Route(id="rt_1", site_id="fac_owner", exit_id="exit_1", length_km=4.2, samples=[], low_share=0.3),
                ExposureSnapshot(
                    id="exp_1", factory_id="fac_owner", mode="replay", forecast_hash="abc",
                    result={"site_risk": 63}, alert=True,
                ),
                StressTest(
                    id="str_1", trigger=Trigger.AUTO, factory_id="fac_owner",
                    params={"hazard": "FLOOD"}, result={"summary": {"orders_at_risk": 3}},
                    exposure_snapshot_id="exp_1",
                ),
                RecoveryRequest(
                    id="rr_1", factory_id="fac_owner", order_id="ord_107",
                    stress_test_id="str_1", status="OPEN",
                ),
                RecoveryStep(id="rs_1", request_id="rr_1", step_key="REQUEST_SENT", state="DONE", at=computed),
                ReadinessSnapshot(
                    id="rdy_1", factory_id="fac_owner", window_hours=48,
                    score=42.0, weighted_score=38.0, breakdown={},
                ),
                Passport(id="pas_1", status=PassportStatus.DRAFT, data={"material": {"value": "EN24"}}),
                Rfq(id="rfq_1", passport_id="pas_1", rfq_ref="RFQ-0001", content={}, text="rfq text"),
                PassportShare(id="sh_1", passport_id="pas_1", partner_id="fac_oragadam", level=ShareLevel.RFQ),
                AppState(key="weather_mode", value={"mode": "replay"}),
            ])
            session.commit()

            assert session.get(StressTest, "str_1").trigger == Trigger.AUTO
            assert session.get(StressTest, "str_1").result == {"summary": {"orders_at_risk": 3}}
            assert session.get(SiteTerrain, "fac_owner").relative_m == pytest.approx(-3.4)
            assert session.get(SiteTerrain, "fac_owner").zone_ids == ["zone_ambattur_north"]
            assert session.get(RecoveryRequest, "rr_1").stress_test_id == "str_1"
            assert session.get(ReadinessSnapshot, "rdy_1").window_hours == 48
            assert session.get(Passport, "pas_1").data["material"]["value"] == "EN24"
            assert session.get(AppState, "weather_mode").value == {"mode": "replay"}


def test_foreign_keys_are_enforced():
    with Session(engine) as session:
        # factory_id FK on machines must reject an unknown factory (PRAGMA foreign_keys=ON).
        orphan = Machine(id="mch_x", factory_id="fac_missing", process=ProcessCode.TURN, name="X")
        session.add(orphan)
        with pytest.raises(Exception):
            session.commit()
        session.rollback()


def test_query_by_fk_index():
    with Session(engine) as session:
        session.add(Factory(id="fac_owner", role=Role.OWNER, name="F", lat=13.1, lon=80.155, cluster_id="c"))
        session.add(Part(id="prt_1", factory_id="fac_owner", name="P", material="EN8", typical_batch_qty=10))
        session.commit()
        rows = session.scalars(select(Part).where(Part.factory_id == "fac_owner")).all()
        assert [part.id for part in rows] == ["prt_1"]