"""Phase 10: M8 readiness core (blueprint section 7.5) - hand-computed numbers.

Tiny world: owner + two partners, three critical parts, two windows. Every
score below is computed by hand from the declared data so a formula change
fails loudly.
"""

from __future__ import annotations

import pytest

from app.config_loader import load_configs
from app.core import readiness as core
from app.enums import BackupStatus, EffectiveStatus, ProcessCode

FAMILIES = {"M1": "steel", "M2": "alloy", "M3": "steel", "M4": "steel"}


def step(seq: int, process: ProcessCode, tolerance: float | None = None) -> core.ReadinessStep:
    return core.ReadinessStep(
        step_id=f"s{seq}", seq=seq, process=process, hours_per_unit=1.0, setup_hours=0.0, tolerance_mm=tolerance
    )


def part(part_id: str, material: str, weight: float, process: ProcessCode, tolerance: float | None = None) -> core.ReadinessPart:
    return core.ReadinessPart(
        part_id=part_id,
        part_name=f"Part {part_id}",
        material=material,
        typical_batch_qty=10,  # 10 h of machine time per step
        weight_inr=weight,
        steps=(step(1, process, tolerance),),
    )


def machine(machine_id: str, process: ProcessCode, tolerance: float | None = 0.02) -> core.ReadinessMachine:
    return core.ReadinessMachine(id=machine_id, process=process, tolerance_mm=tolerance, envelope_mm=None)


def partner(
    partner_id: str,
    relationship_id: str,
    cluster: str,
    grid: str,
    processes: tuple[ProcessCode, ...],
    materials: tuple[str, ...],
    *,
    status: BackupStatus = BackupStatus.READY,
    effective: EffectiveStatus | None = None,
    confirmed_days: float = 5.0,
    distance_hint_km: float = 30.0,
    spare: dict[str, float] | None = None,
    machine_tolerance: float = 0.02,
) -> core.ReadinessPartner:
    lat = 13.0 + distance_hint_km / 111.0
    return core.ReadinessPartner(
        partner_id=partner_id,
        relationship_id=relationship_id,
        name=partner_id,
        lat=lat,
        lon=80.0,
        cluster_id=cluster,
        hazard_zone_id=None,
        grid_id=grid,
        shift_hours_per_day=24.0,  # shift factor 1.0 keeps hand maths trivial
        materials_handled=materials,
        mobilisation_hours=2.0,
        spare_hours_per_week=spare or {"TURN": 200.0, "MILL": 200.0, "GRIND_CYL": 200.0},
        machines=tuple(
            machine(f"{partner_id}_m{i}", process, tolerance=0.005 if process == ProcessCode.GRIND_CYL else machine_tolerance)
            for i, process in enumerate(processes, start=1)
        ),
        status=status,
        effective_status=effective if effective is not None else EffectiveStatus.READY,
        last_confirmed_days_ago=confirmed_days,
    )


OWNER = core.ReadinessOwner(
    factory_id="fac_owner", lat=13.0, lon=80.0, cluster_id="c1", hazard_zone_id="z1", grid_id="g1"
)

# P1 TURN weight 100k; P2 MILL weight 200k; P3 GRIND 0.005 weight 300k
PARTS = [
    part("p1", "M1", 100_000.0, ProcessCode.TURN),
    part("p2", "M2", 200_000.0, ProcessCode.MILL),
    part("p3", "M3", 300_000.0, ProcessCode.GRIND_CYL, tolerance=0.005),
]

PARTNER_A = partner("pa", "rel_a", cluster="c2", grid="g2", processes=(ProcessCode.TURN, ProcessCode.MILL), materials=("M1", "M2"))
PARTNER_B = partner(
    "pb",
    "rel_b",
    cluster="c3",
    grid="g3",
    processes=(ProcessCode.GRIND_CYL,),
    materials=("M3",),
    confirmed_days=120.0,
    distance_hint_km=50.0,
    effective=EffectiveStatus.STALE,
)


@pytest.fixture(scope="module")
def cfg():
    bundle = load_configs()
    return bundle.readiness, bundle.matching


def _compute(partners, windows=(24, 48)) -> core.ReadinessResult:
    readiness_cfg, matching_cfg = load_configs().readiness, load_configs().matching
    return core.compute_readiness(
        PARTS, partners, OWNER, list(windows),
        min_separation_km=readiness_cfg.min_separation_km,
        material_families=FAMILIES,
        logistics_speed_kmh=matching_cfg.logistics_speed_kmh,
        logistics_base_hours=matching_cfg.logistics_base_hours,
    )


def test_hand_computed_three_part_example(cfg):
    """PA covers p1+p2 (fresh READY); PB is stale so p3 is uncovered.

    Lead time for p1 at pa: 2 + (10/1 + 0)*1.0 + 30/35 + 4 = 16.86 h <= 24.
    Weighted: (100k + 200k) / 600k = 50.0. Unweighted: 2/3 = 66.7.
    """
    result = _compute([PARTNER_A, PARTNER_B])
    window = result.windows[0]
    assert window.score == pytest.approx(66.7, abs=0.1)
    assert window.weighted_score == pytest.approx(50.0, abs=0.1)
    assert window.covered_weight_inr == pytest.approx(300_000.0)
    assert window.total_weight_inr == pytest.approx(600_000.0)

    by_part = {item.part_id: item for item in window.breakdown}
    assert by_part["p1"].covered and by_part["p1"].covered_by == "pa"
    assert by_part["p2"].covered and by_part["p2"].covered_by == "pa"
    assert by_part["p3"].reason == core.REASON_STALE
    # windows are monotone: covering at 24 h implies covering at 48 h
    assert result.windows[1].weighted_score == pytest.approx(window.weighted_score)


def test_stale_partner_excluded_and_reconfirm_raises_score(cfg):
    """Invariant 5 mechanics: a stale READY never covers; the counterfactual does."""
    stale = _compute([PARTNER_A, PARTNER_B])
    assert stale.windows[0].weighted_score == pytest.approx(50.0, abs=0.1)

    reconfirmed = _compute([PARTNER_A, replace_ready(PARTNER_B)])
    assert reconfirmed.windows[0].weighted_score == pytest.approx(100.0, abs=0.1)  # +50 by hand
    by_part = {item.part_id: item for item in reconfirmed.windows[0].breakdown}
    assert by_part["p3"].covered and by_part["p3"].covered_by == "pb"


def replace_ready(partner: core.ReadinessPartner) -> core.ReadinessPartner:
    import dataclasses

    return dataclasses.replace(
        partner, status=BackupStatus.READY, effective_status=EffectiveStatus.READY, last_confirmed_days_ago=0.0
    )


def test_uncorrelated_requirements(cfg):
    """Same cluster / zone / grid or < 10 km all count as correlated (section 7.5)."""
    same_cluster = partner("px", "rel_x", cluster="c1", grid="g9", processes=(ProcessCode.TURN,), materials=("M1",))
    same_grid = partner("py", "rel_y", cluster="c9", grid="g1", processes=(ProcessCode.TURN,), materials=("M1",))
    too_close = partner("pz", "rel_z", cluster="c9", grid="g9", processes=(ProcessCode.TURN,), materials=("M1",), distance_hint_km=5.0)
    for bad in (same_cluster, same_grid, too_close):
        result = _compute([bad], windows=(24,))
        by_part = {item.part_id: item for item in result.windows[0].breakdown}
        assert by_part["p1"].reason == core.REASON_CORRELATED, bad.partner_id


def test_reason_ladder_order(cfg):
    """NO_PARTNER_ELIGIBLE beats CORRELATED beats NOT_READY beats NO_CAPACITY beats TOO_SLOW."""
    nobody = _compute([], windows=(48,))
    assert nobody.windows[0].breakdown[0].reason == core.REASON_NO_PARTNER_ELIGIBLE

    # capable but not READY
    pending = partner(
        "pp", "rel_p", cluster="c2", grid="g2", processes=(ProcessCode.TURN,), materials=("M1",),
        status=BackupStatus.APPROVAL_PENDING, effective=EffectiveStatus.APPROVAL_PENDING,
    )
    result = _compute([pending], windows=(48,))
    assert result.windows[0].breakdown[0].reason == core.REASON_NOT_READY

    # READY but insufficient declared capacity for the batch (10 h vs tiny slack)
    tight = partner(
        "pw", "rel_w", cluster="c2", grid="g2", processes=(ProcessCode.TURN,), materials=("M1",),
        spare={"TURN": 10.0},
    )
    result = _compute([tight], windows=(24,))  # 10 <= 10*24/168=1.43? no -> NO_CAPACITY
    assert result.windows[0].breakdown[0].reason == core.REASON_NO_CAPACITY

    # READY, capacity fine at 72, but mobilisation + production + logistics > window
    far = partner(
        "pf", "rel_f", cluster="c2", grid="g2", processes=(ProcessCode.TURN,), materials=("M1",),
        distance_hint_km=900.0,  # 900/35 + 4 = 29.7 h logistics alone
    )
    result = _compute([far], windows=(24,))
    assert result.windows[0].breakdown[0].reason == core.REASON_TOO_SLOW
    result72 = _compute([far], windows=(72,))  # 2 + 10 + 29.7 = 41.7 <= 72 -> covered
    assert result72.windows[0].breakdown[0].covered


def test_lead_time_and_capacity_maths():
    """Unit checks of the two formulas against hand-computed values."""
    p = partner("pm", "rel_m", cluster="c2", grid="g2", processes=(ProcessCode.TURN,), materials=("M1",))
    lead = core.lead_time_hours(PARTS[0], p, 30.0)
    # 2 (mobilisation) + 10 h production (1 machine, shift factor 1) + 30/35 + 4
    assert lead == pytest.approx(2 + 10 + 30 / 35 + 4, abs=0.01)

    # capacity: 10 h batch, spare 200 h/week -> fine at 24 h (200*24/168 = 28.6)
    assert core.capacity_ok(PARTS[0], p, 24) is True
    tight = partner(
        "pt", "rel_t", cluster="c2", grid="g2", processes=(ProcessCode.TURN,), materials=("M1",),
        spare={"TURN": 10.0},
    )
    # 10.0 needed vs 10 * 24/168 = 1.43 h available -> fails; at 168 h exactly 10 -> passes
    assert core.capacity_ok(PARTS[0], tight, 24) is False
    assert core.capacity_ok(PARTS[0], tight, 168) is True


def test_review_flags_stale_and_expiring(cfg):
    readiness_cfg, _matching_cfg = load_configs().readiness, load_configs().matching
    expiring = partner("pe", "rel_e", cluster="c2", grid="g2", processes=(ProcessCode.TURN,), materials=("M1",), confirmed_days=85.0)
    items = core.review_partners([PARTNER_B, expiring], readiness_cfg.staleness_days, readiness_cfg.expiring_soon_days)
    by_partner = {item.partner_id: item for item in items}
    assert by_partner["pb"].effective_status == "STALE"
    assert by_partner["pe"].expiring is True  # 85 days >= 90 - 14
    assert by_partner["pe"].effective_status == "READY"


def test_weight_fallback_for_part_without_orders():
    """The service applies the weight-1 fallback for orderless critical parts (section 7.5);
    the core itself must simply not divide by zero when the weight is 0."""
    no_orders = core.ReadinessPart(
        part_id="p0", part_name="Ghost", material="M1", typical_batch_qty=1, weight_inr=0.0, steps=(step(1, ProcessCode.TURN),)
    )
    result = core.compute_readiness(
        [no_orders], [PARTNER_A], OWNER, [24],
        min_separation_km=10.0, material_families=FAMILIES,
    )
    window = result.windows[0]
    assert window.total_weight_inr == pytest.approx(0.0)
    assert window.weighted_score == pytest.approx(0.0)  # guarded, not a crash
    assert window.score == pytest.approx(100.0)  # unweighted still counts the part as covered