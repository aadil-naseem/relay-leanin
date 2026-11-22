"""M5 hazard effect resolution and downtime windows (blueprint section 7.3). Pure logic.

Maps a hazard, scope, start time and duration into concrete downtime windows
for machines, vendors, suppliers, and site access.

Scope types:
  - zone: matches any site whose hazard_zone_id is in ids, or whose zone_ids contains one
  - cluster: matches any site whose cluster_id is in ids
  - grid: matches any site whose grid_id is in ids
  - sites: explicit site ids
  - exposure_alert: explicit site ids raised by the exposure alert
  - resource: explicit resource ids (for RESOURCE_DOWN)

Hazard effects (section 7.3 table):
  - FLOOD: all machines at affected sites down [start, start+duration];
           vendor/supplier down; site dispatch and inbound blocked.
  - POWER_OUTAGE: same as FLOOD for sites whose grid is in scope.
  - WATER_OUTAGE: only water-dependent processes (HEAT_TREAT, SURFACE_TREAT)
                  and their vendors down; other machines and dispatch keep running.
  - ACCESS_BLOCKED: machines keep running; site dispatch, inbound material,
                    and vendor hand-offs blocked [start, start+duration].
  - RESOURCE_DOWN: exactly the targeted machine/vendor is down [start, start+duration].

No database or FastAPI imports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from app.enums import HazardType, ProcessCode

ScopeType = Literal["zone", "cluster", "grid", "sites", "exposure_alert", "resource"]


@dataclass(frozen=True)
class SiteRef:
    site_id: str
    cluster_id: str | None = None
    hazard_zone_id: str | None = None
    grid_id: str | None = None
    zone_ids: tuple[str, ...] = ()
    is_owner: bool = False


@dataclass(frozen=True)
class ResourceRef:
    resource_id: str  # machine id, vendor id, or supplier id
    site_id: str
    kind: str  # machine | vendor | supplier
    process: ProcessCode | None = None
    water_dependent: bool = False
    available: bool = True


@dataclass(frozen=True)
class DowntimeWindows:
    """Merged, sorted downtime windows in hours from now."""

    # Resource downtime: {resource_id: [(start, end), ...]}
    resource_windows: dict[str, list[tuple[float, float]]] = field(default_factory=dict)
    # Site access blocked (dispatch & inbound): {site_id: [(start, end), ...]}
    site_blocked_windows: dict[str, list[tuple[float, float]]] = field(default_factory=dict)
    # Summaries for reporting / trace
    affected_sites: tuple[str, ...] = ()
    affected_resources: tuple[str, ...] = ()


def merge_windows(windows: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Sort and merge overlapping or adjacent intervals."""
    if not windows:
        return []
    sorted_w = sorted(windows, key=lambda w: (w[0], w[1]))
    merged: list[tuple[float, float]] = [sorted_w[0]]
    for s, e in sorted_w[1:]:
        last_s, last_e = merged[-1]
        if s <= last_e:
            merged[-1] = (last_s, max(last_e, e))
        else:
            merged.append((s, e))
    return merged


def resolve_affected_sites(
    scope_type: ScopeType,
    scope_ids: list[str] | tuple[str, ...],
    sites: list[SiteRef],
) -> set[str]:
    """Find site IDs matching the given scope selector."""
    target_ids = set(scope_ids)
    affected: set[str] = set()

    for site in sites:
        if scope_type in ("sites", "exposure_alert"):
            if site.site_id in target_ids:
                affected.add(site.site_id)
        elif scope_type == "zone":
            if site.hazard_zone_id and site.hazard_zone_id in target_ids:
                affected.add(site.site_id)
            elif any(zid in target_ids for zid in site.zone_ids):
                affected.add(site.site_id)
        elif scope_type == "cluster":
            if site.cluster_id and site.cluster_id in target_ids:
                affected.add(site.site_id)
        elif scope_type == "grid":
            if site.grid_id and site.grid_id in target_ids:
                affected.add(site.site_id)
        elif scope_type == "resource":
            # For resource scope, sites are resolved via resources, not site properties
            pass

    return affected


def build_downtime_windows(
    hazard: HazardType,
    scope_type: ScopeType,
    scope_ids: list[str] | tuple[str, ...],
    start_in_hours: float,
    duration_hours: float,
    sites: list[SiteRef],
    resources: list[ResourceRef],
) -> DowntimeWindows:
    """Build downtime intervals for all resources and site access gates."""
    start = max(0.0, float(start_in_hours))
    duration = max(0.0, float(duration_hours))
    end = start + duration

    window = (start, end)
    resource_windows: dict[str, list[tuple[float, float]]] = {}
    site_blocked_windows: dict[str, list[tuple[float, float]]] = {}
    affected_site_set: set[str] = set()
    affected_res_set: set[str] = set()

    if duration <= 0:
        return DowntimeWindows()

    if hazard == HazardType.RESOURCE_DOWN:
        # Exactly the specified resources go down
        target_res_ids = set(scope_ids)
        for res in resources:
            if res.resource_id in target_res_ids:
                resource_windows.setdefault(res.resource_id, []).append(window)
                affected_res_set.add(res.resource_id)
                affected_site_set.add(res.site_id)
    else:
        # Site-level hazards
        affected_site_set = resolve_affected_sites(scope_type, scope_ids, sites)

        if hazard in (HazardType.FLOOD, HazardType.POWER_OUTAGE):
            # All machines, vendors, suppliers at affected sites go down
            # Site access (dispatch and inbound) is also blocked
            for site_id in affected_site_set:
                site_blocked_windows.setdefault(site_id, []).append(window)

            for res in resources:
                if res.site_id in affected_site_set:
                    resource_windows.setdefault(res.resource_id, []).append(window)
                    affected_res_set.add(res.resource_id)

        elif hazard == HazardType.WATER_OUTAGE:
            # Only water-dependent processes (HEAT_TREAT, SURFACE_TREAT) go down.
            # Other machines continue running; site access is not blocked.
            for res in resources:
                if res.site_id in affected_site_set and res.water_dependent:
                    resource_windows.setdefault(res.resource_id, []).append(window)
                    affected_res_set.add(res.resource_id)

        elif hazard == HazardType.ACCESS_BLOCKED:
            # Machines keep running on the shop floor!
            # Site dispatch, inbound material and vendor hand-offs are blocked.
            for site_id in affected_site_set:
                site_blocked_windows.setdefault(site_id, []).append(window)

    # Merge windows for clean intervals
    merged_res: dict[str, list[tuple[float, float]]] = {
        rid: merge_windows(wins) for rid, wins in resource_windows.items()
    }
    merged_sites: dict[str, list[tuple[float, float]]] = {
        sid: merge_windows(wins) for sid, wins in site_blocked_windows.items()
    }

    return DowntimeWindows(
        resource_windows=merged_res,
        site_blocked_windows=merged_sites,
        affected_sites=tuple(sorted(affected_site_set)),
        affected_resources=tuple(sorted(affected_res_set)),
    )
