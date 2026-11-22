"""M8 service: readiness score, preparedness review, next-best actions (section 7.5).

Every computation writes one `readiness_snapshots` row per window so the UI can
plot the score moving; `record_snapshot` is also called on relationship status
changes and reconfirms (Phase 5 services) so transitions show up in history.

Next-best-actions are **counterfactual recomputes**: for each relationship, the
score is recomputed as if that partner were READY with a fresh confirmation;
the uplift is the real point delta the action would produce at the headline
window. Actions with zero gain are not "next best actions" and are omitted.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config_loader import load_configs
from app.core import readiness as core
from app.core.clock import now
from app.core.status_rules import effective_status as compute_effective_status
from app.core.trace import TraceBuilder
from app.enums import BackupStatus, EffectiveStatus, Role
from app.errors import AppError
from app.models import BackupRelationship, Factory, Machine, Order, Part, ReadinessSnapshot

_SNAPSHOT_INITIAL_REASON = "INITIAL (not yet computed)"


def _material_families() -> dict[str, str]:
    return {material.grade: material.family for material in load_configs().materials}


def _owner(session: Session, factory_id: str) -> Factory:
    factory = session.get(Factory, factory_id)
    if factory is None:
        raise AppError("NOT_FOUND", f"Factory {factory_id!r} does not exist.", status_code=404)
    if factory.role != Role.OWNER:
        raise AppError(
            "NOT_AN_OWNER",
            f"Readiness is computed for an owner factory; {factory_id!r} is a partner.",
            status_code=409,
            details={"factory_id": factory_id, "role": factory.role.value},
        )
    return factory


def _load_world(
    session: Session,
    owner: Factory,
    overrides: dict[str, BackupStatus] | None = None,
) -> tuple[list[core.ReadinessPart], list[core.ReadinessPartner], core.ReadinessOwner]:
    """Critical parts (weighted by open-order value), partners, and the owner context.

    `overrides` forces a relationship's status (and fresh confirmation) for
    counterfactual recomputes without touching the database.
    """
    critical_parts = list(
        session.scalars(
            select(Part).where(Part.factory_id == owner.id, Part.is_critical.is_(True)).order_by(Part.id)
        )
    )
    parts: list[core.ReadinessPart] = []
    for part in critical_parts:
        orders = list(session.scalars(select(Order).where(Order.part_id == part.id)))
        weight = sum(float(order.value_inr) for order in orders)
        steps = tuple(
            core.ReadinessStep(
                step_id=step.id,
                seq=step.seq,
                process=step.process,
                hours_per_unit=float(step.hours_per_unit),
                setup_hours=float(step.setup_hours),
                tolerance_mm=step.tolerance_mm,
            )
            for step in sorted(part.steps, key=lambda s: s.seq)
        )
        parts.append(
            core.ReadinessPart(
                part_id=part.id,
                part_name=part.name,
                material=part.material,
                typical_batch_qty=part.typical_batch_qty,
                weight_inr=round(weight, 2) if weight > 0 else 1.0,  # fallback 1 (section 7.5)
                steps=steps,
            )
        )

    partner_rows = list(session.scalars(select(Factory).where(Factory.role == Role.PARTNER).order_by(Factory.id)))
    machines_by_partner: dict[str, list[core.ReadinessMachine]] = {}
    if partner_rows:
        for machine in session.scalars(
            select(Machine).where(Machine.factory_id.in_([p.id for p in partner_rows])).order_by(Machine.id)
        ):
            machines_by_partner.setdefault(machine.factory_id, []).append(
                core.ReadinessMachine(
                    id=machine.id,
                    process=machine.process,
                    tolerance_mm=machine.achievable_tolerance_mm,
                    envelope_mm=machine.envelope_mm,
                    available=machine.available,
                )
            )

    bundle = load_configs()
    staleness_days = bundle.readiness.staleness_days
    current = now()

    relationships = {
        row.partner_id: row
        for row in session.scalars(
            select(BackupRelationship).where(BackupRelationship.owner_id == owner.id)
        )
    }

    readiness_partners: list[core.ReadinessPartner] = []
    for partner in partner_rows:
        relationship = relationships.get(partner.id)
        if relationship is not None:
            overridden = bool(overrides and relationship.id in overrides)
            status = overrides.get(relationship.id, relationship.status) if overrides else relationship.status
            confirmed_days = 0.0 if overridden else (
                (current - relationship.last_confirmed_at).total_seconds() / 86400.0
                if relationship.last_confirmed_at
                else None
            )
            effective = (
                EffectiveStatus.READY
                if overridden
                else compute_effective_status(
                    relationship.status, relationship.last_confirmed_at, current, staleness_days
                )
            )
            relationship_id: str | None = relationship.id
        else:
            status = BackupStatus.POTENTIAL_MATCH
            effective = EffectiveStatus.POTENTIAL_MATCH
            confirmed_days = None
            relationship_id = None
        readiness_partners.append(
            core.ReadinessPartner(
                partner_id=partner.id,
                relationship_id=relationship_id,
                name=partner.name,
                lat=partner.lat,
                lon=partner.lon,
                cluster_id=partner.cluster_id,
                hazard_zone_id=partner.hazard_zone_id,
                grid_id=partner.grid_id,
                shift_hours_per_day=partner.shift_hours_per_day,
                materials_handled=tuple(partner.materials_handled or []),
                mobilisation_hours=float(partner.mobilisation_hours or 0.0),
                spare_hours_per_week=dict(partner.spare_hours_per_week or {}),
                machines=tuple(machines_by_partner.get(partner.id, ())),
                status=status,
                effective_status=effective,
                last_confirmed_days_ago=confirmed_days,
            )
        )

    owner_ctx = core.ReadinessOwner(
        factory_id=owner.id,
        lat=owner.lat,
        lon=owner.lon,
        cluster_id=owner.cluster_id,
        hazard_zone_id=owner.hazard_zone_id,
        grid_id=owner.grid_id,
    )
    return parts, readiness_partners, owner_ctx


def _core_compute(
    session: Session,
    owner: Factory,
    overrides: dict[str, BackupStatus] | None = None,
) -> tuple[core.ReadinessResult, list[core.PartnerReview], TraceBuilder]:
    bundle = load_configs()
    readiness_cfg = bundle.readiness
    matching_cfg = bundle.matching
    parts, partners, owner_ctx = _load_world(session, owner, overrides)

    trace = TraceBuilder()
    trace.add(
        "load_world",
        f"{len(parts)} critical part(s) weighted by open-order value; {len(partners)} partner(s).",
        inputs={"factory_id": owner.id},
        output={
            "critical_parts": [part.part_id for part in parts],
            "total_weight_inr": round(sum(part.weight_inr for part in parts), 2),
            "stale_partners": sum(1 for p in partners if p.effective_status == EffectiveStatus.STALE),
        },
    )

    result = core.compute_readiness(
        parts,
        partners,
        owner_ctx,
        list(readiness_cfg.windows),
        min_separation_km=readiness_cfg.min_separation_km,
        material_families=_material_families(),
        logistics_speed_kmh=matching_cfg.logistics_speed_kmh,
        logistics_base_hours=matching_cfg.logistics_base_hours,
    )
    for window in result.windows:
        trace.add(
            "window",
            f"{window.window_hours} h: {window.score:.0f} unweighted, {window.weighted_score:.0f} weighted "
            f"(covered INR {window.covered_weight_inr:,.0f} of {window.total_weight_inr:,.0f}).",
            output={
                "breakdown": [
                    {
                        "part_id": item.part_id,
                        "covered": item.covered,
                        "covered_by": item.covered_by,
                        "reason": item.reason,
                        "detail": item.detail,
                    }
                    for item in window.breakdown
                ]
            },
        )
    review = core.review_partners(partners, readiness_cfg.staleness_days, readiness_cfg.expiring_soon_days)
    return result, review, trace


def _write_snapshots(session: Session, owner_id: str, result: core.ReadinessResult, computed_at: datetime) -> None:
    for window in result.windows:
        session.add(
            ReadinessSnapshot(
                id=f"rdy_{uuid.uuid4().hex[:12]}",
                factory_id=owner_id,
                window_hours=window.window_hours,
                score=window.score,
                weighted_score=window.weighted_score,
                breakdown={
                    "covered_weight_inr": window.covered_weight_inr,
                    "total_weight_inr": window.total_weight_inr,
                    "parts": [
                        {
                            "part_id": item.part_id,
                            "covered": item.covered,
                            "covered_by": item.covered_by,
                            "reason": item.reason,
                        }
                        for item in window.breakdown
                    ],
                },
                reason=f"COMPUTED windows={','.join(str(w.window_hours) for w in result.windows)}",
                computed_at=computed_at,
            )
        )
    session.commit()


def readiness_out(session: Session, factory_id: str, window_hours: int | None = None) -> dict:
    """Full readiness payload for GET /readiness/{id}."""
    owner = _owner(session, factory_id)
    bundle = load_configs()
    cfg = bundle.readiness
    headline = window_hours if window_hours is not None else cfg.default_window_hours
    if headline not in cfg.windows:
        raise AppError(
            "VALIDATION_ERROR",
            f"window must be one of {cfg.windows}",
            status_code=422,
            details={"allowed": list(cfg.windows)},
        )

    result, review, trace = _core_compute(session, owner)
    headline_window = next(w for w in result.windows if w.window_hours == headline)
    computed_at = now()
    _write_snapshots(session, owner.id, result, computed_at)

    relationship_rows = {
        row.id: row
        for row in session.scalars(
            select(BackupRelationship).where(BackupRelationship.owner_id == owner.id)
        )
    }
    review_out = []
    for item in review:
        row = relationship_rows.get(item.relationship_id)
        review_out.append(
            {
                "relationship_id": item.relationship_id,
                "partner_id": item.partner_id,
                "partner_name": item.partner_name,
                "status": item.status,
                "effective_status": item.effective_status,
                "last_confirmed_at": row.last_confirmed_at if row else None,
                "days_since_confirm": item.days_since_confirm,
                "expiring": item.expiring,
                "action": "reconfirm",
            }
        )

    return {
        "factory_id": owner.id,
        "window_hours": headline,
        "score": headline_window.score,
        "weighted_score": headline_window.weighted_score,
        "windows": [
            {"window_hours": w.window_hours, "score": w.score, "weighted_score": w.weighted_score}
            for w in result.windows
        ],
        "breakdown": [
            {
                "part_id": item.part_id,
                "part_name": item.part_name,
                "weight_inr": item.weight_inr,
                "covered": item.covered,
                "covered_by": item.covered_by,
                "backup_status": item.backup_status,
                "reason": item.reason,
                "detail": item.detail,
            }
            for item in headline_window.breakdown
        ],
        "review": review_out,
        "stale_partners": result.stale_partners,
        "trace": trace.to_list(),
    }


def actions_out(session: Session, factory_id: str, window_hours: int | None = None) -> dict:
    """Next-best actions with counterfactual uplift (section 7.5)."""
    owner = _owner(session, factory_id)
    bundle = load_configs()
    cfg = bundle.readiness
    headline = window_hours if window_hours is not None else cfg.default_window_hours

    baseline, _review, trace = _core_compute(session, owner)
    baseline_window = next(w for w in baseline.windows if w.window_hours == headline)

    relationships = list(
        session.scalars(select(BackupRelationship).where(BackupRelationship.owner_id == owner.id))
    )
    actions: list[dict] = []
    for relationship in relationships:
        if relationship.status == BackupStatus.UNAVAILABLE_EXPIRED:
            continue
        # counterfactual: this partner READY with a fresh confirmation
        overrides = {relationship.id: BackupStatus.READY}
        counterfactual, _rev, _t = _core_compute(session, owner, overrides=overrides)
        cf_window = next(w for w in counterfactual.windows if w.window_hours == headline)
        uplift = round(cf_window.weighted_score - baseline_window.weighted_score, 1)
        if uplift <= 0:
            continue
        actions.append(
            {
                "relationship_id": relationship.id,
                "partner_id": relationship.partner_id,
                "label": _action_label(session, relationship),
                "uplift_points": uplift,
                "current_score": baseline_window.weighted_score,
                "projected_score": cf_window.weighted_score,
            }
        )
    actions.sort(key=lambda item: (-item["uplift_points"], item["partner_id"]))
    trace.add(
        "actions",
        f"{len(actions)} action(s) with a positive uplift at the {headline} h window.",
        output={"actions": actions[:5]},
    )
    return {
        "factory_id": owner.id,
        "window_hours": headline,
        "actions": actions[:5],  # top 5 by point gain (section 7.5)
        "trace": trace.to_list(),
    }


def _action_label(session: Session, relationship: BackupRelationship) -> str:
    partner = session.get(Factory, relationship.partner_id)
    name = partner.name if partner else relationship.partner_id
    if relationship.status == BackupStatus.READY:
        return f"Reconfirm {name}"
    return f"Complete checks and set {name} READY"


def history_out(session: Session, factory_id: str) -> dict:
    """Score timeline for the UI (every computed snapshot; INITIAL rows excluded)."""
    owner = _owner(session, factory_id)
    rows = list(
        session.scalars(
            select(ReadinessSnapshot)
            .where(ReadinessSnapshot.factory_id == owner.id)
            .order_by(ReadinessSnapshot.computed_at, ReadinessSnapshot.window_hours)
        )
    )
    points = [
        {
            "computed_at": row.computed_at,
            "window_hours": row.window_hours,
            "score": row.score,
            "weighted_score": row.weighted_score,
        }
        for row in rows
        if row.reason != _SNAPSHOT_INITIAL_REASON
    ]
    return {"factory_id": owner.id, "points": points}


def record_snapshot(session: Session, factory_id: str) -> None:
    """Write readiness snapshots now (called on status changes and reconfirms)."""
    owner = session.get(Factory, factory_id)
    if owner is None or owner.role != Role.OWNER:
        return
    result, _review, _trace = _core_compute(session, owner)
    _write_snapshots(session, owner.id, result, now())
