"""Unit tests for core/hazards.py: scope resolution and hazard-to-downtime rules."""

from __future__ import annotations

from app.core.hazards import (
    ResourceRef,
    SiteRef,
    build_downtime_windows,
    resolve_affected_sites,
)
from app.enums import HazardType, ProcessCode


def _sample_world():
    sites = [
        SiteRef(site_id="fac_1", cluster_id="cl_north", hazard_zone_id="zone_a", grid_id="grid_1", is_owner=True),
        SiteRef(site_id="fac_2", cluster_id="cl_north", hazard_zone_id=None, grid_id="grid_1", is_owner=False),
        SiteRef(site_id="ven_1", cluster_id="cl_south", hazard_zone_id="zone_b", grid_id="grid_2", is_owner=False),
    ]
    resources = [
        ResourceRef(resource_id="mch_turn_1", site_id="fac_1", kind="machine", process=ProcessCode.TURN, water_dependent=False),
        ResourceRef(resource_id="mch_heat_1", site_id="fac_1", kind="machine", process=ProcessCode.HEAT_TREAT, water_dependent=True),
        ResourceRef(resource_id="mch_mill_2", site_id="fac_2", kind="machine", process=ProcessCode.MILL, water_dependent=False),
        ResourceRef(resource_id="ven_heat_1", site_id="ven_1", kind="vendor", process=ProcessCode.HEAT_TREAT, water_dependent=True),
    ]
    return sites, resources


def test_resolve_affected_sites_by_scope():
    sites, _ = _sample_world()

    # Sites scope
    assert resolve_affected_sites("sites", ["fac_1", "ven_1"], sites) == {"fac_1", "ven_1"}

    # Zone scope
    assert resolve_affected_sites("zone", ["zone_a"], sites) == {"fac_1"}
    assert resolve_affected_sites("zone", ["zone_b"], sites) == {"ven_1"}
    assert resolve_affected_sites("zone", ["zone_unknown"], sites) == set()

    # Cluster scope
    assert resolve_affected_sites("cluster", ["cl_north"], sites) == {"fac_1", "fac_2"}

    # Grid scope
    assert resolve_affected_sites("grid", ["grid_1"], sites) == {"fac_1", "fac_2"}
    assert resolve_affected_sites("grid", ["grid_2"], sites) == {"ven_1"}

    # Exposure alert scope
    assert resolve_affected_sites("exposure_alert", ["fac_1"], sites) == {"fac_1"}


def test_flood_hazard_takes_all_machines_and_blocks_site():
    sites, resources = _sample_world()

    downtime = build_downtime_windows(
        hazard=HazardType.FLOOD,
        scope_type="zone",
        scope_ids=["zone_a"],
        start_in_hours=12.0,
        duration_hours=24.0,
        sites=sites,
        resources=resources,
    )

    # fac_1 is in zone_a
    assert downtime.affected_sites == ("fac_1",)
    assert set(downtime.affected_resources) == {"mch_turn_1", "mch_heat_1"}

    # Both machines at fac_1 have downtime [12, 36]
    assert downtime.resource_windows["mch_turn_1"] == [(12.0, 36.0)]
    assert downtime.resource_windows["mch_heat_1"] == [(12.0, 36.0)]

    # Site access blocked [12, 36]
    assert downtime.site_blocked_windows["fac_1"] == [(12.0, 36.0)]

    # fac_2 and ven_1 unaffected
    assert "mch_mill_2" not in downtime.resource_windows
    assert "ven_heat_1" not in downtime.resource_windows
    assert "fac_2" not in downtime.site_blocked_windows


def test_power_outage_hazard():
    sites, resources = _sample_world()

    downtime = build_downtime_windows(
        hazard=HazardType.POWER_OUTAGE,
        scope_type="grid",
        scope_ids=["grid_1"],
        start_in_hours=5.0,
        duration_hours=10.0,
        sites=sites,
        resources=resources,
    )

    # Both fac_1 and fac_2 are on grid_1
    assert set(downtime.affected_sites) == {"fac_1", "fac_2"}
    assert set(downtime.affected_resources) == {"mch_turn_1", "mch_heat_1", "mch_mill_2"}
    assert downtime.site_blocked_windows["fac_1"] == [(5.0, 15.0)]
    assert downtime.site_blocked_windows["fac_2"] == [(5.0, 15.0)]


def test_water_outage_only_hits_water_dependent_resources():
    sites, resources = _sample_world()

    downtime = build_downtime_windows(
        hazard=HazardType.WATER_OUTAGE,
        scope_type="cluster",
        scope_ids=["cl_north"],
        start_in_hours=0.0,
        duration_hours=48.0,
        sites=sites,
        resources=resources,
    )

    # fac_1 and fac_2 are in cl_north
    assert set(downtime.affected_sites) == {"fac_1", "fac_2"}
    # Only mch_heat_1 is water_dependent! mch_turn_1 and mch_mill_2 keep running!
    assert downtime.affected_resources == ("mch_heat_1",)
    assert downtime.resource_windows["mch_heat_1"] == [(0.0, 48.0)]
    assert "mch_turn_1" not in downtime.resource_windows
    assert "mch_mill_2" not in downtime.resource_windows

    # Site access is NOT blocked during water outage
    assert len(downtime.site_blocked_windows) == 0


def test_access_blocked_keeps_machines_running():
    sites, resources = _sample_world()

    downtime = build_downtime_windows(
        hazard=HazardType.ACCESS_BLOCKED,
        scope_type="sites",
        scope_ids=["fac_1"],
        start_in_hours=10.0,
        duration_hours=15.0,
        sites=sites,
        resources=resources,
    )

    assert downtime.affected_sites == ("fac_1",)
    # Machines KEEP RUNNING on shop floor: zero resource downtime
    assert len(downtime.resource_windows) == 0
    # Site dispatch/inbound is blocked
    assert downtime.site_blocked_windows["fac_1"] == [(10.0, 25.0)]


def test_resource_down_targets_single_resource():
    sites, resources = _sample_world()

    downtime = build_downtime_windows(
        hazard=HazardType.RESOURCE_DOWN,
        scope_type="resource",
        scope_ids=["mch_turn_1"],
        start_in_hours=8.0,
        duration_hours=16.0,
        sites=sites,
        resources=resources,
    )

    assert downtime.affected_resources == ("mch_turn_1",)
    assert downtime.resource_windows["mch_turn_1"] == [(8.0, 24.0)]
    # Other machines at fac_1 and site access unaffected
    assert "mch_heat_1" not in downtime.resource_windows
    assert len(downtime.site_blocked_windows) == 0
