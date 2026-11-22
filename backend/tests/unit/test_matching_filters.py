"""Unit tests for core/matching.py: hard filters (process, material, tolerance, envelope, capacity, lead time)."""

from __future__ import annotations

from app.core.matching import (
    OrderMatchRequirement,
    PartnerCandidateInfo,
    PartnerMachineInfo,
    StepMatchRequirement,
    evaluate_hard_filters,
)
from app.enums import BackupStatus, EffectiveStatus, ProcessCode

MATERIAL_FAMILIES = {
    "EN8": "carbon_steel",
    "C45": "carbon_steel",
    "EN24": "alloy_steel",
    "SS304": "stainless_steel",
    "Al6061": "aluminium",
}


def _dummy_partner(
    machines: list[PartnerMachineInfo] | None = None,
    materials: list[str] | None = None,
    spare_hours: dict[str, float] | None = None,
    effective_status: EffectiveStatus = EffectiveStatus.READY,
    last_confirmed_days: float | None = 20.0,
    mobilisation: float = 4.0,
    shift_hours: float = 16.0,
) -> PartnerCandidateInfo:
    return PartnerCandidateInfo(
        partner_id="fac_part_1",
        name="Test Partner",
        lat=13.0,
        lon=80.0,
        cluster_id="cl_test",
        hazard_zone_id=None,
        grid_id="grid_test",
        shift_hours_per_day=shift_hours,
        materials_handled=tuple(materials or ["EN8", "SS304"]),
        typical_lead_time_hours=48.0,
        mobilisation_hours=mobilisation,
        spare_hours_per_week=spare_hours or {"TURN": 40.0, "MILL": 40.0},
        machines=tuple(machines or [
            PartnerMachineInfo(id="m_1", process=ProcessCode.TURN, tolerance_mm=0.02, envelope_mm=300.0),
            PartnerMachineInfo(id="m_2", process=ProcessCode.MILL, tolerance_mm=0.05, envelope_mm=400.0),
        ]),
        status=BackupStatus.READY,
        effective_status=effective_status,
        last_confirmed_days_ago=last_confirmed_days,
    )


def test_process_filter_pass_and_fail():
    # Order needs TURN and MILL
    order = OrderMatchRequirement(
        order_id="ord_1",
        part_id="prt_1",
        part_name="Shaft",
        qty=10,
        due_in_hours=50.0,
        material="EN8",
        steps=(
            StepMatchRequirement(step_id="s1", seq=1, process=ProcessCode.TURN, hours_per_unit=0.1, setup_hours=1.0),
            StepMatchRequirement(step_id="s2", seq=2, process=ProcessCode.MILL, hours_per_unit=0.1, setup_hours=1.0),
        ),
    )

    # Capable partner
    p_ok = _dummy_partner()
    evals = {f.key: f for f in evaluate_hard_filters(order, p_ok, distance_km=20.0, material_families=MATERIAL_FAMILIES)}
    assert evals["process"].result == "PASS"

    # Partner missing MILL machine
    p_missing = _dummy_partner(
        machines=[PartnerMachineInfo(id="m_1", process=ProcessCode.TURN, tolerance_mm=0.02)]
    )
    evals_missing = {f.key: f for f in evaluate_hard_filters(order, p_missing, distance_km=20.0, material_families=MATERIAL_FAMILIES)}
    assert evals_missing["process"].result == "FAIL"
    assert "MILL" in evals_missing["process"].detail


def test_material_filter_exact_family_and_fail():
    order = OrderMatchRequirement(
        order_id="ord_1", part_id="prt_1", part_name="Shaft", qty=10, due_in_hours=50.0, material="EN8", steps=()
    )

    # Exact match: partner handles EN8
    p_exact = _dummy_partner(materials=["EN8"])
    f_exact = {f.key: f for f in evaluate_hard_filters(order, p_exact, distance_km=20.0, material_families=MATERIAL_FAMILIES)}
    assert f_exact["material"].result == "PASS"

    # Family match: partner handles C45 (both carbon_steel)
    p_family = _dummy_partner(materials=["C45"])
    f_family = {f.key: f for f in evaluate_hard_filters(order, p_family, distance_km=20.0, material_families=MATERIAL_FAMILIES)}
    assert f_family["material"].result == "PASS"

    # Fail: partner handles only Al6061
    p_fail = _dummy_partner(materials=["Al6061"])
    f_fail = {f.key: f for f in evaluate_hard_filters(order, p_fail, distance_km=20.0, material_families=MATERIAL_FAMILIES)}
    assert f_fail["material"].result == "FAIL"


def test_tolerance_filter_pass_and_fail():
    # Step requires tight tolerance 0.005 mm
    order = OrderMatchRequirement(
        order_id="ord_1",
        part_id="prt_1",
        part_name="Precision Pin",
        qty=10,
        due_in_hours=50.0,
        material="EN8",
        steps=(
            StepMatchRequirement(
                step_id="s1", seq=1, process=ProcessCode.GRIND_CYL, hours_per_unit=0.2, setup_hours=1.0, tolerance_mm=0.005
            ),
        ),
    )

    # Partner has grinder capable of 0.005 mm
    p_ok = _dummy_partner(
        machines=[PartnerMachineInfo(id="m_g1", process=ProcessCode.GRIND_CYL, tolerance_mm=0.005)]
    )
    f_ok = {f.key: f for f in evaluate_hard_filters(order, p_ok, distance_km=20.0, material_families=MATERIAL_FAMILIES)}
    assert f_ok["tolerance"].result == "PASS"

    # Partner grinder can only hold 0.01 mm
    p_fail = _dummy_partner(
        machines=[PartnerMachineInfo(id="m_g2", process=ProcessCode.GRIND_CYL, tolerance_mm=0.010)]
    )
    f_fail = {f.key: f for f in evaluate_hard_filters(order, p_fail, distance_km=20.0, material_families=MATERIAL_FAMILIES)}
    assert f_fail["tolerance"].result == "FAIL"


def test_envelope_filter_pass_and_fail():
    # Part envelope 500 mm
    order = OrderMatchRequirement(
        order_id="ord_1",
        part_id="prt_1",
        part_name="Big Flange",
        qty=1,
        due_in_hours=50.0,
        material="EN8",
        steps=(StepMatchRequirement(step_id="s1", seq=1, process=ProcessCode.MILL, hours_per_unit=1.0, setup_hours=0.0),),
        envelope_mm=500.0,
    )

    # Machine accepts up to 600 mm
    p_ok = _dummy_partner(
        machines=[PartnerMachineInfo(id="m1", process=ProcessCode.MILL, envelope_mm=600.0)]
    )
    f_ok = {f.key: f for f in evaluate_hard_filters(order, p_ok, distance_km=20.0, material_families=MATERIAL_FAMILIES)}
    assert f_ok["envelope"].result == "PASS"

    # Machine accepts only up to 400 mm
    p_fail = _dummy_partner(
        machines=[PartnerMachineInfo(id="m2", process=ProcessCode.MILL, envelope_mm=400.0)]
    )
    f_fail = {f.key: f for f in evaluate_hard_filters(order, p_fail, distance_km=20.0, material_families=MATERIAL_FAMILIES)}
    assert f_fail["envelope"].result == "FAIL"


def test_capacity_filter_pass_fail_and_stale_unknown():
    # Order requires 100 units * 0.5h + 2h = 52 hours of TURN
    order = OrderMatchRequirement(
        order_id="ord_1",
        part_id="prt_1",
        part_name="Shaft",
        qty=100,
        due_in_hours=168.0,  # 1 week horizon -> full weekly spare hours available
        material="EN8",
        steps=(StepMatchRequirement(step_id="s1", seq=1, process=ProcessCode.TURN, hours_per_unit=0.5, setup_hours=2.0),),
    )

    # Partner has 60h spare capacity -> PASS
    p_ok = _dummy_partner(spare_hours={"TURN": 60.0})
    f_ok = {f.key: f for f in evaluate_hard_filters(order, p_ok, distance_km=20.0, material_families=MATERIAL_FAMILIES)}
    assert f_ok["capacity"].result == "PASS"

    # Partner has only 30h spare capacity -> FAIL
    p_fail = _dummy_partner(spare_hours={"TURN": 30.0})
    f_fail = {f.key: f for f in evaluate_hard_filters(order, p_fail, distance_km=20.0, material_families=MATERIAL_FAMILIES)}
    assert f_fail["capacity"].result == "FAIL"

    # Partner confirmation is STALE (> 90 days) -> UNKNOWN
    p_stale = _dummy_partner(
        spare_hours={"TURN": 100.0},
        effective_status=EffectiveStatus.STALE,
        last_confirmed_days=120.0,
    )
    f_stale = {f.key: f for f in evaluate_hard_filters(order, p_stale, distance_km=20.0, material_families=MATERIAL_FAMILIES)}
    assert f_stale["capacity"].result == "UNKNOWN"
    assert "stale" in f_stale["capacity"].detail


def test_lead_time_filter_pass_and_fail():
    order = OrderMatchRequirement(
        order_id="ord_1",
        part_id="prt_1",
        part_name="Shaft",
        qty=10,
        due_in_hours=50.0,  # buffer 24h -> 26h deadline buffer
        material="EN8",
        steps=(StepMatchRequirement(step_id="s1", seq=1, process=ProcessCode.TURN, hours_per_unit=0.5, setup_hours=1.0),),
    )

    # Nearby partner (35 km -> 1h travel + 4h base = 5h logistics; 4h mobilisation; 6h work -> total 15h <= 26h)
    p_near = _dummy_partner(mobilisation=4.0)
    f_near = {f.key: f for f in evaluate_hard_filters(order, p_near, distance_km=35.0, material_families=MATERIAL_FAMILIES)}
    assert f_near["lead_time"].result == "PASS"

    # Far partner with large mobilisation (800 km -> 23h logistics + 16h mob + 6h work = 45h > 26h buffer)
    p_far = _dummy_partner(mobilisation=16.0)
    f_far = {f.key: f for f in evaluate_hard_filters(order, p_far, distance_km=800.0, material_families=MATERIAL_FAMILIES)}
    assert f_far["lead_time"].result == "FAIL"
