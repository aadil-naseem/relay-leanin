"""Unit tests for core/matching.py: candidate ranking formula and greedy diverse set selection."""

from __future__ import annotations

from app.core.matching import (
    CandidateEvaluation,
    FilterEvaluation,
    OrderMatchRequirement,
    PartnerCandidateInfo,
    StepMatchRequirement,
    calculate_ranking_score,
    select_recommended_set,
)
from app.enums import BackupStatus, EffectiveStatus, ProcessCode

STATUS_WEIGHTS = {
    "READY": 1.0,
    "APPROVAL_PENDING": 0.6,
    "ASSESSMENT_IN_PROGRESS": 0.4,
    "POTENTIAL_MATCH": 0.2,
    "UNAVAILABLE_EXPIRED": 0.0,
}

RANKING_WEIGHTS = {
    "status": 0.40,
    "time_slack": 0.20,
    "capacity_slack": 0.15,
    "freshness": 0.15,
    "separation": 0.10,
}


def _dummy_order():
    return OrderMatchRequirement(
        order_id="ord_1",
        part_id="prt_1",
        part_name="Shaft",
        qty=10,
        due_in_hours=72.0,
        material="EN8",
        steps=(
            StepMatchRequirement(step_id="s1", seq=1, process=ProcessCode.TURN, hours_per_unit=0.1, setup_hours=1.0),
        ),
    )


def test_ranking_score_reflects_status_and_freshness():
    order = _dummy_order()

    # 1. Fresh READY partner
    p_ready = PartnerCandidateInfo(
        partner_id="p_ready",
        name="Ready Partner",
        lat=12.8,
        lon=79.9,
        cluster_id="cl_1",
        hazard_zone_id=None,
        grid_id="grid_1",
        shift_hours_per_day=16.0,
        materials_handled=("EN8",),
        typical_lead_time_hours=48.0,
        mobilisation_hours=4.0,
        spare_hours_per_week={"TURN": 50.0},
        machines=(),
        status=BackupStatus.READY,
        effective_status=EffectiveStatus.READY,
        last_confirmed_days_ago=10.0,
    )
    score_ready = calculate_ranking_score(
        p_ready, order, distance_km=40.0, status_weights=STATUS_WEIGHTS, ranking_weights=RANKING_WEIGHTS
    )

    # 2. Stale READY partner (status weight 0.5, lower freshness)
    p_stale = PartnerCandidateInfo(
        partner_id="p_stale",
        name="Stale Partner",
        lat=12.8,
        lon=79.9,
        cluster_id="cl_1",
        hazard_zone_id=None,
        grid_id="grid_1",
        shift_hours_per_day=16.0,
        materials_handled=("EN8",),
        typical_lead_time_hours=48.0,
        mobilisation_hours=4.0,
        spare_hours_per_week={"TURN": 50.0},
        machines=(),
        status=BackupStatus.READY,
        effective_status=EffectiveStatus.STALE,
        last_confirmed_days_ago=110.0,
    )
    score_stale = calculate_ranking_score(
        p_stale, order, distance_km=40.0, status_weights=STATUS_WEIGHTS, ranking_weights=RANKING_WEIGHTS
    )

    # 3. APPROVAL_PENDING partner
    p_pending = PartnerCandidateInfo(
        partner_id="p_pending",
        name="Pending Partner",
        lat=12.8,
        lon=79.9,
        cluster_id="cl_1",
        hazard_zone_id=None,
        grid_id="grid_1",
        shift_hours_per_day=16.0,
        materials_handled=("EN8",),
        typical_lead_time_hours=48.0,
        mobilisation_hours=4.0,
        spare_hours_per_week={"TURN": 50.0},
        machines=(),
        status=BackupStatus.APPROVAL_PENDING,
        effective_status=EffectiveStatus.APPROVAL_PENDING,
        last_confirmed_days_ago=10.0,
    )
    score_pending = calculate_ranking_score(
        p_pending, order, distance_km=40.0, status_weights=STATUS_WEIGHTS, ranking_weights=RANKING_WEIGHTS
    )

    # Assert expected ordering: Fresh READY > APPROVAL_PENDING > Stale READY
    assert score_ready > score_pending > score_stale


def test_select_recommended_set_avoids_correlated_pairs():
    # 3 candidates:
    # c1: Oragadam (high score, cluster A, grid South, 37 km)
    # c2: Neighbor of Oragadam (slightly lower score, cluster A, same grid South, 40 km)
    # c3: Hosur (good score, cluster B, grid Hosur, 270 km)
    p1 = PartnerCandidateInfo(
        partner_id="p1", name="Oragadam", lat=12.8, lon=79.9, cluster_id="cl_oragadam", hazard_zone_id=None,
        grid_id="grid_south", shift_hours_per_day=16.0, materials_handled=("EN8",), typical_lead_time_hours=48.0,
        mobilisation_hours=4.0, spare_hours_per_week={}, machines=(), status=BackupStatus.READY,
        effective_status=EffectiveStatus.READY, last_confirmed_days_ago=10.0,
    )
    p2_corr = PartnerCandidateInfo(
        partner_id="p2", name="Oragadam Neighbor", lat=12.85, lon=79.92, cluster_id="cl_oragadam", hazard_zone_id=None,
        grid_id="grid_south", shift_hours_per_day=16.0, materials_handled=("EN8",), typical_lead_time_hours=48.0,
        mobilisation_hours=4.0, spare_hours_per_week={}, machines=(), status=BackupStatus.READY,
        effective_status=EffectiveStatus.READY, last_confirmed_days_ago=10.0,
    )
    p3_div = PartnerCandidateInfo(
        partner_id="p3", name="Hosur", lat=12.7, lon=77.8, cluster_id="cl_hosur", hazard_zone_id=None,
        grid_id="grid_hosur", shift_hours_per_day=16.0, materials_handled=("EN8",), typical_lead_time_hours=48.0,
        mobilisation_hours=8.0, spare_hours_per_week={}, machines=(), status=BackupStatus.APPROVAL_PENDING,
        effective_status=EffectiveStatus.APPROVAL_PENDING, last_confirmed_days_ago=10.0,
    )

    partner_map = {"p1": p1, "p2": p2_corr, "p3": p3_div}

    dummy_filter = (FilterEvaluation(key="process", result="PASS", basis="test", detail="ok"),)

    c1 = CandidateEvaluation(
        partner_id="p1", name="Oragadam", status=BackupStatus.READY, effective_status=EffectiveStatus.READY,
        distance_km=37.0, filters=dummy_filter, unverified=(), excluded=False, exclusion_reason=None,
        flags=(), score=85.0,
    )
    c2 = CandidateEvaluation(
        partner_id="p2", name="Oragadam Neighbor", status=BackupStatus.READY, effective_status=EffectiveStatus.READY,
        distance_km=40.0, filters=dummy_filter, unverified=(), excluded=False, exclusion_reason=None,
        flags=(), score=82.0,  # Higher score than p3, but shares cluster and grid!
    )
    c3 = CandidateEvaluation(
        partner_id="p3", name="Hosur", status=BackupStatus.APPROVAL_PENDING, effective_status=EffectiveStatus.APPROVAL_PENDING,
        distance_km=270.0, filters=dummy_filter, unverified=(), excluded=False, exclusion_reason=None,
        flags=(), score=72.0,  # Lower score, but diverse cluster and grid!
    )

    selected = select_recommended_set([c1, c2, c3], partner_map, k=2)
    assert selected is not None
    chosen_ids, note = selected

    # Should choose c1 (Oragadam) and c3 (Hosur) because c2 is penalized for sharing cluster and grid!
    assert chosen_ids == ("p1", "p3")
    assert "Hosur" in note
    assert "Oragadam" in note
    assert "independent power grids" in note
