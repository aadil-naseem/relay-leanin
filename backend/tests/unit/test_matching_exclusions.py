"""Unit tests for core/matching.py: correlated risk exclusions (SAME_CLUSTER, SAME_HAZARD_ZONE, SAME_GRID, ALSO_EXPOSED_SAME_EVENT, NEARBY)."""

from __future__ import annotations

from app.core.matching import AffectedSiteContext, PartnerCandidateInfo, evaluate_correlated_risk
from app.enums import BackupStatus, EffectiveStatus, HazardType


def _dummy_partner(
    partner_id: str = "fac_part",
    cluster_id: str | None = "cl_distant",
    hazard_zone_id: str | None = None,
    grid_id: str | None = "grid_distinct",
    site_risk: int | None = 20,
) -> PartnerCandidateInfo:
    return PartnerCandidateInfo(
        partner_id=partner_id,
        name="Candidate Partner",
        lat=12.8,
        lon=79.9,
        cluster_id=cluster_id,
        hazard_zone_id=hazard_zone_id,
        grid_id=grid_id,
        shift_hours_per_day=16.0,
        materials_handled=("EN8",),
        typical_lead_time_hours=48.0,
        mobilisation_hours=6.0,
        spare_hours_per_week={"TURN": 40.0},
        machines=(),
        status=BackupStatus.READY,
        effective_status=EffectiveStatus.READY,
        last_confirmed_days_ago=15.0,
        site_risk=site_risk,
    )


def test_exclude_same_cluster():
    context = AffectedSiteContext(
        site_id="fac_owner",
        cluster_id="cl_ambattur",
        hazard_zone_id="zone_ambattur_north",
        grid_id="grid_chennai_metro",
        lat=13.1,
        lon=80.1,
    )
    # Partner in the same cluster
    p = _dummy_partner(cluster_id="cl_ambattur", hazard_zone_id=None)
    excluded, reason, flags = evaluate_correlated_risk(p, context, distance_km=5.0)

    assert excluded is True
    assert reason == "SAME_CLUSTER"


def test_exclude_same_hazard_zone():
    context = AffectedSiteContext(
        site_id="fac_owner",
        cluster_id="cl_ambattur",
        hazard_zone_id="zone_ambattur_north",
        grid_id="grid_chennai_metro",
        lat=13.1,
        lon=80.1,
    )
    # Partner in different cluster but same flood zone
    p = _dummy_partner(cluster_id="cl_other", hazard_zone_id="zone_ambattur_north")
    excluded, reason, flags = evaluate_correlated_risk(p, context, distance_km=15.0)

    assert excluded is True
    assert reason == "SAME_HAZARD_ZONE"


def test_exclude_same_grid_under_power_outage():
    context = AffectedSiteContext(
        site_id="fac_owner",
        cluster_id="cl_ambattur",
        hazard_zone_id=None,
        grid_id="grid_chennai_metro",
        lat=13.1,
        lon=80.1,
        hazard=HazardType.POWER_OUTAGE,
    )
    # Under POWER_OUTAGE, matching grid is strictly excluded
    p_same_grid = _dummy_partner(cluster_id="cl_guindy", grid_id="grid_chennai_metro")
    excluded, reason, flags = evaluate_correlated_risk(p_same_grid, context, distance_km=15.0)

    assert excluded is True
    assert reason == "SAME_GRID"

    # Under FLOOD, matching grid is flagged SAME_GRID but not excluded by grid alone
    context_flood = AffectedSiteContext(
        site_id="fac_owner",
        cluster_id="cl_ambattur",
        hazard_zone_id=None,
        grid_id="grid_chennai_metro",
        lat=13.1,
        lon=80.1,
        hazard=HazardType.FLOOD,
    )
    excluded_flood, reason_flood, flags_flood = evaluate_correlated_risk(p_same_grid, context_flood, distance_km=15.0)
    assert excluded_flood is False
    assert "SAME_GRID" in flags_flood


def test_exclude_also_exposed_same_event():
    context = AffectedSiteContext(
        site_id="fac_owner",
        cluster_id="cl_ambattur",
        hazard_zone_id=None,
        grid_id="grid_chennai_metro",
        lat=13.1,
        lon=80.1,
        hazard=HazardType.FLOOD,
        affected_site_ids=("fac_owner", "ven_heat", "fac_guindy"),
    )
    # fac_guindy is in the affected storm footprint
    p_exposed = _dummy_partner(partner_id="fac_guindy", cluster_id="cl_guindy")
    excluded, reason, flags = evaluate_correlated_risk(p_exposed, context, distance_km=15.0)

    assert excluded is True
    assert reason == "ALSO_EXPOSED_SAME_EVENT"

    # Alternatively, partner whose live forecast risk >= 50 is excluded
    p_high_risk = _dummy_partner(partner_id="fac_other", cluster_id="cl_other", site_risk=65)
    ex2, reason2, _ = evaluate_correlated_risk(p_high_risk, context, distance_km=25.0, alert_threshold=50)
    assert ex2 is True
    assert reason2 == "ALSO_EXPOSED_SAME_EVENT"


def test_non_excluded_safe_candidate():
    context = AffectedSiteContext(
        site_id="fac_owner",
        cluster_id="cl_ambattur",
        hazard_zone_id="zone_ambattur_north",
        grid_id="grid_chennai_metro",
        lat=13.1,
        lon=80.1,
    )
    # Oragadam: different cluster, no flood zone, different grid, low site risk, 37 km away
    p_safe = _dummy_partner(
        partner_id="fac_oragadam",
        cluster_id="cl_oragadam",
        hazard_zone_id=None,
        grid_id="grid_kanchi_south",
        site_risk=30,
    )
    excluded, reason, flags = evaluate_correlated_risk(p_safe, context, distance_km=37.0)

    assert excluded is False
    assert reason is None
    assert "NEARBY" not in flags
