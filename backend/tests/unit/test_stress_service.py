"""Unit tests for services/stress.py and api/stress.py: manual test, auto-run, idempotency, story invariants."""

from __future__ import annotations

from sqlalchemy import select

from app.api import stress as stress_api
from app.core.clock import now
from app.db import SessionLocal
from app.demo_seed import reset_demo
from app.enums import HazardType, Trigger
from app.errors import AppError
from app.models import ExposureSnapshot, StressTest
from app.schemas.stress import ScopeIn, StressCreate
from app.services import stress as stress_service


def test_manual_flood_stress_test_seeded_world():
    """Blueprint Done-When: A manual FLOOD test on the owner factory produces LATE orders with sensible dates."""
    reset_demo()
    session = SessionLocal()
    try:
        create_payload = StressCreate(
            factory_id="fac_owner",
            hazard=HazardType.FLOOD,
            scope=ScopeIn(type="zone", ids=["zone_ambattur_north"]),
            start_in_hours=24.0,
            duration_hours=72.0,
        )

        result = stress_service.run_manual_stress_test(session, create_payload)

        assert result.factory_id == "fac_owner"
        assert result.hazard == HazardType.FLOOD
        assert result.trigger == Trigger.MANUAL
        assert "fac_owner" in result.affected_sites

        # Section 9 invariant 2 assertions:
        # orders_at_risk >= 2, revenue_exposed_inr >= 1,000,000, orders_no_fallback >= 1
        assert result.summary.orders_at_risk >= 2
        assert result.summary.revenue_exposed_inr >= 1_000_000.0
        assert result.summary.orders_no_fallback >= 1

        # Check headline
        assert "Flood scenario:" in result.headline
        assert "exposed" in result.headline

        # Verify trace is populated
        step_names = [t.step for t in result.trace]
        assert "load_world" in step_names
        assert "hazard_windows" in step_names
        assert "simulation" in step_names

        # Check DB persistence
        db_row = session.get(StressTest, result.id)
        assert db_row is not None
        assert db_row.trigger == Trigger.MANUAL
        assert db_row.result["summary"]["orders_at_risk"] == result.summary.orders_at_risk
    finally:
        session.close()


def test_get_stress_test_and_404():
    reset_demo()
    session = SessionLocal()
    try:
        create_payload = StressCreate(
            factory_id="fac_owner",
            hazard=HazardType.RESOURCE_DOWN,
            scope=ScopeIn(type="resource", ids=["mch_own_grind_1"]),
            start_in_hours=10.0,
            duration_hours=20.0,
        )
        created = stress_service.run_manual_stress_test(session, create_payload)

        fetched = stress_service.get_stress_test(session, created.id)
        assert fetched.id == created.id
        assert fetched.hazard == HazardType.RESOURCE_DOWN

        # 404 test
        try:
            stress_service.get_stress_test(session, "str_does_not_exist")
            assert False, "Expected 404 AppError"
        except AppError as e:
            assert e.code == "NOT_FOUND"
            assert e.status_code == 404
    finally:
        session.close()


def test_auto_run_for_alert_and_idempotency():
    """Blueprint Task 4: Auto-run function run_auto_for_alert(exposure_snapshot) is idempotent."""
    reset_demo()
    session = SessionLocal()
    try:
        # Create an ExposureSnapshot row simulating an alert
        snapshot_id = "exp_test_alert_12345"
        forecast_hash = "abc1234567890def1234567890abcdef"
        snapshot = ExposureSnapshot(
            id=snapshot_id,
            factory_id="fac_owner",
            mode="replay",
            computed_at=now(),
            forecast_hash=forecast_hash,
            alert=True,
            result={
                "alert": {
                    "active": True,
                    "level": "SEVERE",
                    "onset_in_hours": 23.0,
                    "max_24h_mm": 238.7,
                    "affected_sites": ["fac_owner", "ven_heat", "sup_steel"],
                    "headline": "Severe rain alert",
                },
                "sites": {
                    "fac_owner": {"wet_spell_hours": 40.0},
                    "ven_heat": {"wet_spell_hours": 40.0},
                    "sup_steel": {"wet_spell_hours": 40.0},
                },
            },
        )
        session.add(snapshot)
        session.commit()

        count_before = len(list(session.scalars(select(StressTest))))

        # First auto run: should compute and insert StressTest row
        auto_res_1 = stress_service.run_auto_for_alert(session, snapshot)
        assert auto_res_1 is not None
        assert auto_res_1.trigger == Trigger.AUTO
        assert auto_res_1.exposure_snapshot_id == snapshot_id
        assert auto_res_1.summary.orders_at_risk >= 2
        assert auto_res_1.summary.revenue_exposed_inr >= 1_000_000.0
        assert "Heavy rain in 23h:" in auto_res_1.headline

        count_after_first = len(list(session.scalars(select(StressTest))))
        assert count_after_first == count_before + 1

        # Second auto run: MUST be idempotent and return identical result without new rows
        auto_res_2 = stress_service.run_auto_for_alert(session, snapshot)
        assert auto_res_2 is not None
        assert auto_res_2.id == auto_res_1.id
        assert auto_res_2.summary == auto_res_1.summary
        assert auto_res_2.headline == auto_res_1.headline

        count_after_second = len(list(session.scalars(select(StressTest))))
        assert count_after_second == count_after_first
    finally:
        session.close()


def test_stress_api_endpoints_directly():
    """Verify router functions produce valid schemas directly."""
    reset_demo()
    session = SessionLocal()
    try:
        create_payload = StressCreate(
            factory_id="fac_owner",
            hazard=HazardType.ACCESS_BLOCKED,
            scope=ScopeIn(type="sites", ids=["fac_owner"]),
            start_in_hours=12.0,
            duration_hours=24.0,
        )

        created = stress_api.create_stress_test(body=create_payload, db=session)
        assert created.hazard == HazardType.ACCESS_BLOCKED
        assert created.summary.orders_at_risk >= 0

        fetched = stress_api.get_stress_test(test_id=created.id, db=session)
        assert fetched.id == created.id
    finally:
        session.close()
