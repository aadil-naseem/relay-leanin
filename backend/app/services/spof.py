"""M3 service: build the resource/requirement world from the database (section 7.1).

Loads the owner's own machines, its approved vendors and suppliers, the active
orders with their part routes, and the static exposure flag (zone membership).
Live exposure (site risk at or above the alert threshold) is joined in Phase 13,
when M4 exists; the `exposed` flag here is therefore zone-based and documented
as such in the trace.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import spof as engine
from app.core.trace import TraceBuilder
from app.enums import Role
from app.errors import AppError
from app.models import Factory, Machine, Order, Part, SiteTerrain, Vendor, VendorLink


def _exposed_site_ids(session: Session, site_ids: set[str]) -> set[str]:
    """Static exposure: a hazard zone on the site row or derived zone membership."""
    exposed: set[str] = set()
    if not site_ids:
        return exposed
    for factory in session.scalars(select(Factory).where(Factory.id.in_(site_ids))):
        if factory.hazard_zone_id:
            exposed.add(factory.id)
    for vendor in session.scalars(select(Vendor).where(Vendor.id.in_(site_ids))):
        if vendor.hazard_zone_id:
            exposed.add(vendor.id)
    for terrain in session.scalars(select(SiteTerrain).where(SiteTerrain.site_id.in_(site_ids))):
        if terrain.zone_ids:
            exposed.add(terrain.site_id)
    return exposed


def _part_envelope(session: Session, part: Part) -> float | None:
    """Part envelope comes from the passport when one exists (section 7.6 field)."""
    if part.passport_id is None:
        return None
    from app.models import Passport

    passport = session.get(Passport, part.passport_id)
    if passport is None:
        return None
    field_value = (passport.data or {}).get("envelope_mm") or {}
    value = field_value.get("value") if isinstance(field_value, dict) else field_value
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def build_world(session: Session, factory_id: str) -> tuple[list[engine.Resource], list[engine.OrderRequirement]]:
    factory = session.get(Factory, factory_id)
    if factory is None:
        raise AppError("NOT_FOUND", f"Factory {factory_id!r} does not exist.", status_code=404)
    if factory.role != Role.OWNER:
        raise AppError(
            "NOT_AN_OWNER",
            f"SPOF analysis is for an owner factory; {factory_id!r} is a partner.",
            status_code=409,
            details={"factory_id": factory_id, "role": factory.role.value},
        )

    resources: list[engine.Resource] = []

    # in-house machines
    for machine in session.scalars(select(Machine).where(Machine.factory_id == factory_id).order_by(Machine.id)):
        resources.append(
            engine.Resource(
                id=machine.id,
                kind=engine.KIND_MACHINE,
                name=machine.name,
                site_id=factory_id,
                process=machine.process,
                tolerance_mm=machine.achievable_tolerance_mm,
                envelope_mm=machine.envelope_mm,
                available=machine.available,
            )
        )

    # approved vendors and suppliers
    linked = session.scalars(select(VendorLink).where(VendorLink.factory_id == factory_id)).all()
    for link in linked:
        vendor = session.get(Vendor, link.vendor_id)
        if vendor is None:
            continue
        kind = engine.KIND_VENDOR if vendor.kind.value == "VENDOR" else engine.KIND_SUPPLIER
        resources.append(
            engine.Resource(
                id=vendor.id,
                kind=kind,
                name=vendor.name,
                site_id=vendor.id,
                process=vendor.process,
                material=vendor.material,
                available=True,
            )
        )

    # active orders with their part routes
    orders: list[engine.OrderRequirement] = []
    order_rows = session.scalars(select(Order).where(Order.factory_id == factory_id).order_by(Order.id)).all()
    for order in order_rows:
        part = session.get(Part, order.part_id)
        if part is None:
            continue
        envelope = _part_envelope(session, part)
        steps = tuple(
            engine.StepRequirement(
                step_id=step.id,
                seq=step.seq,
                process=step.process,
                tolerance_mm=step.tolerance_mm,
                outsourced=step.outsourced,
                envelope_mm=envelope,
            )
            for step in sorted(part.steps, key=lambda s: s.seq)
        )
        orders.append(
            engine.OrderRequirement(
                order_id=order.id,
                part_id=part.id,
                part_name=part.name,
                value_inr=float(order.value_inr),
                material=part.material,
                steps=steps,
            )
        )
    return resources, orders


def compute_spof(session: Session, factory_id: str) -> tuple[engine.SpofResult, list[dict]]:
    resources, orders = build_world(session, factory_id)
    exposed = _exposed_site_ids(session, {resource.site_id for resource in resources})

    result = engine.find_spofs(orders, resources, exposed_sites=exposed)

    trace = TraceBuilder()
    trace.add(
        "load_world",
        f"{len(orders)} active orders, {len(resources)} resources "
        f"({sum(1 for r in resources if r.kind == engine.KIND_MACHINE)} machines, "
        f"{sum(1 for r in resources if r.kind == engine.KIND_VENDOR)} vendors, "
        f"{sum(1 for r in resources if r.kind == engine.KIND_SUPPLIER)} suppliers).",
        inputs={"factory_id": factory_id},
        output={
            "orders": len(orders),
            "exposure_flag": "zone membership (live exposure joined in Phase 13)",
            "exposed_sites": sorted(exposed),
        },
    )
    trace.add(
        "coverage",
        "For each requirement (every step + the material), the set of resources that can serve it "
        "was computed; tolerance and envelope filters applied for machines.",
        output={
            "uncovered_requirements": list(result.uncovered_requirements),
            "unavailable_resources_excluded": list(result.excluded_resources),
        },
    )
    for item in result.items:
        trace.add(
            "remove_resource",
            f"Remove {item.name} ({item.kind}) -> {len(item.orders_broken)} order(s) lose their only server: "
            f"{', '.join(item.orders_broken)}.",
            inputs={"resource_id": item.resource_id},
            output={"revenue_at_risk_inr": item.revenue_at_risk_inr, "exposed": item.exposed},
        )
    trace.add(
        "rank",
        "Ranked by revenue at risk desc, then order count (section 7.1).",
        output={"top": [item.resource_id for item in result.items[:5]], "spof_count": len(result.items)},
    )
    return result, trace.to_list()