"""M5 service: build inputs from DB, run stress simulation, persist results (section 7.3).

Orchestrates:
  - Database loads for factory, machines, linked vendors/suppliers, orders, and parts.
  - Scope resolution and downtime window construction via core/hazards.py.
  - List scheduling (baseline vs stressed) via core/scheduler.py.
  - Calculation trace generation.
  - Persistence of StressTest rows with full JSON payload.
  - Idempotent auto-run for exposure alerts.
"""

from __future__ import annotations

import uuid
from datetime import timedelta
from threading import Lock
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config_loader import load_configs
from app.core import hazards, scheduler
from app.core.clock import now
from app.core.trace import TraceBuilder
from app.enums import FallbackLevel, HazardType, Trigger
from app.errors import AppError
from app.models import (
    ExposureSnapshot,
    Factory,
    Machine,
    Order,
    Part,
    PartStep,
    SiteTerrain,
    StressTest,
    Vendor,
    VendorLink,
)
from app.schemas.common import TraceEntry
from app.schemas.stress import OrderImpact, ScopeIn, StressCreate, StressOut, StressSummary

_AUTO_STRESS_LOCK = Lock()


def format_inr_short(value: float) -> str:
    """Format an INR amount into plain lakhs / crores."""
    if value >= 10_000_000:
        cr = value / 10_000_000
        return f"₹{cr:.1f} Cr" if cr != int(cr) else f"₹{int(cr)} Cr"
    if value >= 100_000:
        lakh = value / 100_000
        return f"₹{lakh:.1f} L" if lakh != int(lakh) else f"₹{int(lakh)} L"
    return f"₹{value:,.0f}"


def _build_headline(
    hazard: HazardType,
    summary: StressSummary,
    onset_in_hours: float | None = None,
    trigger: Trigger = Trigger.MANUAL,
) -> str:
    """Generate a clean, honest headline for the stress test result."""
    if trigger == Trigger.AUTO and onset_in_hours is not None:
        lead_str = f"{int(onset_in_hours)}h" if onset_in_hours == int(onset_in_hours) else f"{onset_in_hours:.1f}h"
        headline = (
            f"Heavy rain in {lead_str}: {summary.orders_at_risk} order(s) at risk, "
            f"{format_inr_short(summary.revenue_exposed_inr)} exposed"
        )
    else:
        labels = {
            HazardType.FLOOD: "Flood scenario",
            HazardType.POWER_OUTAGE: "Power outage scenario",
            HazardType.WATER_OUTAGE: "Water outage scenario",
            HazardType.ACCESS_BLOCKED: "Access blocked scenario",
            HazardType.RESOURCE_DOWN: "Resource disruption",
        }
        prefix = labels.get(hazard, "Disruption scenario")
        headline = (
            f"{prefix}: {summary.orders_at_risk} order(s) at risk, "
            f"{format_inr_short(summary.revenue_exposed_inr)} exposed"
        )

    if summary.orders_no_fallback > 0:
        headline += f", {summary.orders_no_fallback} order(s) have no fallback"

    return headline


def _load_simulation_world(
    session: Session,
    factory_id: str,
) -> tuple[
    Factory,
    list[scheduler.OrderScheduleInput],
    list[scheduler.MachineScheduleInput],
    list[scheduler.VendorScheduleInput],
    list[scheduler.SupplierScheduleInput],
    list[hazards.SiteRef],
    list[hazards.ResourceRef],
    dict[str, Order],
]:
    """Load and shape entities from the database into pure scheduler inputs."""
    factory = session.get(Factory, factory_id)
    if factory is None:
        raise AppError("NOT_FOUND", f"Factory {factory_id!r} not found.", status_code=404)

    configs = load_configs()
    processes_cfg = configs.processes

    # 1. Machines for the factory
    db_machines = list(
        session.scalars(select(Machine).where(Machine.factory_id == factory_id).order_by(Machine.id))
    )
    sched_machines: list[scheduler.MachineScheduleInput] = []
    res_refs: list[hazards.ResourceRef] = []

    for m in db_machines:
        is_water_dep = False
        if m.process and m.process.value in processes_cfg:
            is_water_dep = processes_cfg[m.process.value].water_dependent

        sched_machines.append(
            scheduler.MachineScheduleInput(
                id=m.id,
                process=m.process,
                tolerance_mm=m.achievable_tolerance_mm,
                envelope_mm=m.envelope_mm,
                available=m.available,
            )
        )
        res_refs.append(
            hazards.ResourceRef(
                resource_id=m.id,
                site_id=factory_id,
                kind="machine",
                process=m.process,
                water_dependent=is_water_dep,
                available=m.available,
            )
        )

    # 2. Linked Vendors & Suppliers
    vendor_links = list(
        session.scalars(select(VendorLink).where(VendorLink.factory_id == factory_id))
    )
    linked_vendor_ids = {vl.vendor_id for vl in vendor_links}
    db_vendors = list(
        session.scalars(select(Vendor).where(Vendor.id.in_(linked_vendor_ids)).order_by(Vendor.id))
    ) if linked_vendor_ids else []

    sched_vendors: list[scheduler.VendorScheduleInput] = []
    sched_suppliers: list[scheduler.SupplierScheduleInput] = []

    for v in db_vendors:
        is_water_dep = False
        if v.process and v.process.value in processes_cfg:
            is_water_dep = processes_cfg[v.process.value].water_dependent

        if v.kind.value == "VENDOR":
            sched_vendors.append(
                scheduler.VendorScheduleInput(
                    id=v.id,
                    process=v.process,  # type: ignore[arg-type]
                    turnaround_hours=float(v.turnaround_hours),
                    available=True,
                )
            )
            res_refs.append(
                hazards.ResourceRef(
                    resource_id=v.id,
                    site_id=v.id,  # vendors have their own site location
                    kind="vendor",
                    process=v.process,
                    water_dependent=is_water_dep,
                    available=True,
                )
            )
        elif v.kind.value == "SUPPLIER":
            sched_suppliers.append(
                scheduler.SupplierScheduleInput(
                    id=v.id,
                    material=v.material or "",
                    turnaround_hours=float(v.turnaround_hours),
                    available=True,
                )
            )
            res_refs.append(
                hazards.ResourceRef(
                    resource_id=v.id,
                    site_id=v.id,
                    kind="supplier",
                    process=None,
                    water_dependent=False,
                    available=True,
                )
            )

    # 3. All known sites (factories + linked vendors) for scope resolution
    terrain_by_site = {row.site_id: row for row in session.scalars(select(SiteTerrain))}
    site_refs: list[hazards.SiteRef] = []

    # Owner site
    owner_terrain = terrain_by_site.get(factory_id)
    site_refs.append(
        hazards.SiteRef(
            site_id=factory.id,
            cluster_id=factory.cluster_id,
            hazard_zone_id=factory.hazard_zone_id,
            grid_id=factory.grid_id,
            zone_ids=tuple(owner_terrain.zone_ids) if owner_terrain and owner_terrain.zone_ids else (),
            is_owner=True,
        )
    )

    # Vendor sites
    for v in db_vendors:
        v_terrain = terrain_by_site.get(v.id)
        site_refs.append(
            hazards.SiteRef(
                site_id=v.id,
                cluster_id=v.cluster_id,
                hazard_zone_id=v.hazard_zone_id,
                grid_id=v.grid_id,
                zone_ids=tuple(v_terrain.zone_ids) if v_terrain and v_terrain.zone_ids else (),
                is_owner=False,
            )
        )

    # 4. Orders and Part steps
    db_orders = list(
        session.scalars(select(Order).where(Order.factory_id == factory_id).order_by(Order.due_at, Order.id))
    )
    part_ids = {o.part_id for o in db_orders}
    db_parts = {p.id: p for p in session.scalars(select(Part).where(Part.id.in_(part_ids)))} if part_ids else {}

    db_steps_list = list(
        session.scalars(select(PartStep).where(PartStep.part_id.in_(part_ids)).order_by(PartStep.part_id, PartStep.seq))
    ) if part_ids else []

    steps_by_part: dict[str, list[scheduler.StepScheduleInput]] = {}
    for ps in db_steps_list:
        steps_by_part.setdefault(ps.part_id, []).append(
            scheduler.StepScheduleInput(
                step_id=ps.id,
                seq=ps.seq,
                process=ps.process,
                hours_per_unit=float(ps.hours_per_unit),
                setup_hours=float(ps.setup_hours),
                tolerance_mm=ps.tolerance_mm,
                envelope_mm=None,  # could join passport envelope if available
                outsourced=ps.outsourced,
            )
        )

    sched_orders: list[scheduler.OrderScheduleInput] = []
    order_map: dict[str, Order] = {}
    current_time_utc = now()

    for o in db_orders:
        order_map[o.id] = o
        part = db_parts.get(o.part_id)
        part_name = part.name if part else o.part_id
        material = part.material if part else ""
        due_diff = (o.due_at - current_time_utc).total_seconds() / 3600.0

        sched_orders.append(
            scheduler.OrderScheduleInput(
                order_id=o.id,
                part_id=o.part_id,
                part_name=part_name,
                qty=o.qty,
                due_in_hours=max(0.0, due_diff),
                value_inr=float(o.value_inr),
                material=material,
                steps=tuple(steps_by_part.get(o.part_id, [])),
            )
        )

    return factory, sched_orders, sched_machines, sched_vendors, sched_suppliers, site_refs, res_refs, order_map


def _serialize_stress_out(
    test_id: str,
    trigger: Trigger,
    hazard: HazardType,
    factory_id: str,
    sim_result: scheduler.StressSimulationResult,
    order_map: dict[str, Order],
    start_time_utc: Any,
    headline: str,
    params: dict,
    exposure_snapshot_id: str | None,
    created_at: Any,
    trace_entries: list[dict],
) -> StressOut:
    """Build the final Pydantic StressOut object."""
    impacts: list[OrderImpact] = []
    for eval_order in sim_result.orders:
        o_db = order_map.get(eval_order.order_id)
        due_at = o_db.due_at if o_db else (start_time_utc + timedelta(hours=eval_order.due_in_hours))
        base_finish_at = start_time_utc + timedelta(hours=eval_order.baseline_finish_hours)
        str_finish_at = start_time_utc + timedelta(hours=eval_order.stressed_finish_hours)

        impacts.append(
            OrderImpact(
                order_id=eval_order.order_id,
                part_id=eval_order.part_id,
                state=eval_order.state,
                due_at=due_at,
                stressed_finish_at=str_finish_at,
                baseline_finish_at=base_finish_at,
                days_late=eval_order.days_late,
                value_inr=eval_order.value_inr,
                fallback_level=eval_order.fallback_level,
                best_backup=eval_order.best_backup,
            )
        )

    summary = StressSummary(
        orders_at_risk=sim_result.orders_at_risk,
        revenue_exposed_inr=sim_result.revenue_exposed_inr,
        orders_no_fallback=sim_result.orders_no_fallback,
        orders_no_ready_fallback=sim_result.orders_no_ready_fallback,
    )

    return StressOut(
        id=test_id,
        trigger=trigger,
        hazard=hazard,
        factory_id=factory_id,
        affected_sites=list(sim_result.affected_sites),
        orders=impacts,
        summary=summary,
        headline=headline,
        params=params,
        exposure_snapshot_id=exposure_snapshot_id,
        created_at=created_at,
        trace=[TraceEntry(**t) for t in trace_entries],
    )


def run_manual_stress_test(session: Session, payload: StressCreate) -> StressOut:
    """Run a manual what-if stress test (POST /stress-tests)."""
    trace = TraceBuilder()
    current_time = now()
    configs = load_configs()
    due_buffer_hours = configs.stress.due_buffer_hours
    transport_hours = configs.stress.transport_hours

    factory, orders, machines, vendors, suppliers, site_refs, res_refs, order_map = _load_simulation_world(
        session, payload.factory_id
    )

    trace.add(
        "load_world",
        f"Loaded {len(orders)} order(s), {len(machines)} machine(s), {len(vendors)} vendor(s), "
        f"{len(suppliers)} supplier(s) for factory {factory.id}.",
        inputs={"factory_id": factory.id, "hazard": payload.hazard.value, "scope": payload.scope.model_dump()},
    )

    # 1. Build downtime windows
    downtime = hazards.build_downtime_windows(
        hazard=payload.hazard,
        scope_type=payload.scope.type,
        scope_ids=payload.scope.ids,
        start_in_hours=payload.start_in_hours,
        duration_hours=payload.duration_hours,
        sites=site_refs,
        resources=res_refs,
    )

    trace.add(
        "hazard_windows",
        f"Hazard {payload.hazard.value} affected {len(downtime.affected_sites)} site(s) and "
        f"{len(downtime.affected_resources)} resource(s) from t={payload.start_in_hours}h to "
        f"t={payload.start_in_hours + payload.duration_hours}h.",
        output={
            "affected_sites": list(downtime.affected_sites),
            "affected_resources": list(downtime.affected_resources),
            "resource_windows_count": len(downtime.resource_windows),
        },
    )

    from app.services import matching as matching_service

    def _resolve_manual_fallback(o: scheduler.OrderScheduleInput) -> tuple[FallbackLevel, str | None]:
        match_out = matching_service.find_matches_for_order(
            session,
            o.order_id,
            scenario={"hazard": payload.hazard.value, "affected_sites": list(downtime.affected_sites)},
        )
        return match_out.fallback_level, match_out.best_backup

    # 2. Run simulation
    sim_result = scheduler.run_stress_simulation(
        orders=orders,
        factory_id=factory.id,
        shift_hours_per_day=factory.shift_hours_per_day,
        machines=machines,
        vendors=vendors,
        suppliers=suppliers,
        downtime=downtime,
        due_buffer_hours=due_buffer_hours,
        transport_hours=transport_hours,
        fallback_resolver=_resolve_manual_fallback,
    )

    trace.add(
        "simulation",
        f"Simulation finished: {sim_result.orders_at_risk} order(s) at risk, "
        f"revenue exposed ₹{sim_result.revenue_exposed_inr:,.0f}.",
        output={
            "orders_at_risk": sim_result.orders_at_risk,
            "revenue_exposed_inr": sim_result.revenue_exposed_inr,
            "orders_no_fallback": sim_result.orders_no_fallback,
        },
    )

    summary_stub = StressSummary(
        orders_at_risk=sim_result.orders_at_risk,
        revenue_exposed_inr=sim_result.revenue_exposed_inr,
        orders_no_fallback=sim_result.orders_no_fallback,
        orders_no_ready_fallback=sim_result.orders_no_ready_fallback,
    )
    headline = _build_headline(
        hazard=payload.hazard,
        summary=summary_stub,
        trigger=Trigger.MANUAL,
    )

    test_id = f"str_man_{uuid.uuid4().hex[:12]}"
    params_dict = payload.model_dump()

    stress_out = _serialize_stress_out(
        test_id=test_id,
        trigger=Trigger.MANUAL,
        hazard=payload.hazard,
        factory_id=factory.id,
        sim_result=sim_result,
        order_map=order_map,
        start_time_utc=current_time,
        headline=headline,
        params=params_dict,
        exposure_snapshot_id=None,
        created_at=current_time,
        trace_entries=trace.to_list(),
    )

    # Persist in DB
    db_row = StressTest(
        id=test_id,
        trigger=Trigger.MANUAL,
        factory_id=factory.id,
        params=params_dict,
        result=stress_out.model_dump(mode="json"),
        exposure_snapshot_id=None,
        created_at=current_time,
    )
    session.add(db_row)
    session.commit()

    return stress_out


def run_auto_for_alert(
    session: Session,
    exposure_snapshot: ExposureSnapshot,
) -> StressOut | None:
    """Serialize auto-run creation in-process; the deterministic ID handles retries."""
    with _AUTO_STRESS_LOCK:
        return _run_auto_for_alert(session, exposure_snapshot)


def _run_auto_for_alert(
    session: Session,
    exposure_snapshot: ExposureSnapshot,
) -> StressOut | None:
    """Run or reuse the auto stress test triggered by an exposure alert (idempotent)."""
    if not exposure_snapshot.alert:
        return None

    factory_id = exposure_snapshot.factory_id
    forecast_hash = exposure_snapshot.forecast_hash

    # Check for existing auto stress test for this (factory_id, forecast_hash)
    existing_row = session.scalar(
        select(StressTest).where(
            StressTest.factory_id == factory_id,
            StressTest.trigger == Trigger.AUTO,
            StressTest.exposure_snapshot_id == exposure_snapshot.id,
        )
    )
    if existing_row is not None and existing_row.result:
        return StressOut(**existing_row.result)

    # Derive parameters from exposure snapshot
    alert_info = exposure_snapshot.result.get("alert", {})
    affected_sites = list(alert_info.get("affected_sites") or [factory_id])
    onset_in_hours = float(alert_info.get("onset_in_hours") if alert_info.get("onset_in_hours") is not None else 24.0)
    level = alert_info.get("level") or "HIGH"

    configs = load_configs()
    recession = configs.exposure.recession_hours.get(level, 24.0)

    # Calculate wet spell from affected sites in the snapshot
    sites_info = exposure_snapshot.result.get("sites", {})
    spells = [
        float(sites_info[sid]["wet_spell_hours"])
        for sid in affected_sites
        if sid in sites_info and sites_info[sid].get("wet_spell_hours") is not None
    ]
    wet_spell = max(spells, default=24.0)
    duration_hours = min(wet_spell, configs.exposure.wet_spell_cap_hours) + float(recession)

    trace = TraceBuilder()
    current_time = now()
    due_buffer_hours = configs.stress.due_buffer_hours
    transport_hours = configs.stress.transport_hours

    factory, orders, machines, vendors, suppliers, site_refs, res_refs, order_map = _load_simulation_world(
        session, factory_id
    )

    trace.add(
        "auto_trigger",
        f"Auto stress test triggered by exposure alert (level={level}, onset={onset_in_hours}h).",
        inputs={
            "factory_id": factory_id,
            "forecast_hash": forecast_hash,
            "onset_in_hours": onset_in_hours,
            "duration_hours": duration_hours,
            "affected_sites": affected_sites,
        },
    )

    downtime = hazards.build_downtime_windows(
        hazard=HazardType.FLOOD,
        scope_type="exposure_alert",
        scope_ids=affected_sites,
        start_in_hours=onset_in_hours,
        duration_hours=duration_hours,
        sites=site_refs,
        resources=res_refs,
    )

    from app.services import matching as matching_service

    def _resolve_auto_fallback(o: scheduler.OrderScheduleInput) -> tuple[FallbackLevel, str | None]:
        match_out = matching_service.find_matches_for_order(
            session,
            o.order_id,
            scenario={"hazard": HazardType.FLOOD.value, "affected_sites": list(downtime.affected_sites)},
        )
        return match_out.fallback_level, match_out.best_backup

    sim_result = scheduler.run_stress_simulation(
        orders=orders,
        factory_id=factory.id,
        shift_hours_per_day=factory.shift_hours_per_day,
        machines=machines,
        vendors=vendors,
        suppliers=suppliers,
        downtime=downtime,
        due_buffer_hours=due_buffer_hours,
        transport_hours=transport_hours,
        fallback_resolver=_resolve_auto_fallback,
    )

    summary_stub = StressSummary(
        orders_at_risk=sim_result.orders_at_risk,
        revenue_exposed_inr=sim_result.revenue_exposed_inr,
        orders_no_fallback=sim_result.orders_no_fallback,
        orders_no_ready_fallback=sim_result.orders_no_ready_fallback,
    )
    headline = _build_headline(
        hazard=HazardType.FLOOD,
        summary=summary_stub,
        onset_in_hours=onset_in_hours,
        trigger=Trigger.AUTO,
    )

    test_id = f"str_auto_{forecast_hash[:16]}_{factory_id}"
    params_dict = {
        "factory_id": factory_id,
        "hazard": HazardType.FLOOD.value,
        "scope": ScopeIn(type="exposure_alert", ids=affected_sites).model_dump(),
        "start_in_hours": onset_in_hours,
        "duration_hours": duration_hours,
        "forecast_hash": forecast_hash,
    }

    stress_out = _serialize_stress_out(
        test_id=test_id,
        trigger=Trigger.AUTO,
        hazard=HazardType.FLOOD,
        factory_id=factory.id,
        sim_result=sim_result,
        order_map=order_map,
        start_time_utc=current_time,
        headline=headline,
        params=params_dict,
        exposure_snapshot_id=exposure_snapshot.id,
        created_at=current_time,
        trace_entries=trace.to_list(),
    )

    # Save idempotent row
    db_row = StressTest(
        id=test_id,
        trigger=Trigger.AUTO,
        factory_id=factory.id,
        params=params_dict,
        result=stress_out.model_dump(mode="json"),
        exposure_snapshot_id=exposure_snapshot.id,
        created_at=current_time,
    )
    session.add(db_row)
    try:
        session.commit()
    except IntegrityError:
        # A second worker may win the same deterministic auto-run between the
        # lookup above and this insert. Roll back, then return the committed row.
        session.rollback()
        existing_row = session.scalar(select(StressTest).where(StressTest.id == test_id))
        if existing_row is None or not existing_row.result:
            raise
        return StressOut(**existing_row.result)

    return stress_out


def get_stress_test(session: Session, test_id: str) -> StressOut:
    """Retrieve an existing stress test result by its ID."""
    row = session.get(StressTest, test_id)
    if row is None or not row.result:
        raise AppError("NOT_FOUND", f"Stress test {test_id!r} not found.", status_code=404)
    return StressOut(**row.result)
