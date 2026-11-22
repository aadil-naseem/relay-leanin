"""M6 service: candidate loading, live exposure joining, matching orchestration (section 7.4)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config_loader import load_configs
from app.core import matching as core_matching
from app.core.clock import now
from app.core.status_rules import effective_status as compute_effective_status
from app.core.trace import TraceBuilder
from app.enums import BackupStatus, CheckKey, EffectiveStatus, HazardType, Role
from app.errors import AppError
from app.models import (
    BackupRelationship,
    ExposureSnapshot,
    Factory,
    Machine,
    Order,
    Part,
    PartStep,
    RelationshipCheck,
)
from app.schemas.common import TraceEntry
from app.schemas.matching import (
    CandidateOut,
    FilterResult,
    MatchingOut,
    RecommendedSet,
)
from app.services import exposure as exposure_service


def _load_material_families() -> dict[str, str]:
    """Map canonical material grades and aliases to their material family."""
    configs = load_configs()
    families: dict[str, str] = {}
    for mat in configs.materials:
        families[mat.grade] = mat.family
        families[mat.grade.upper()] = mat.family
        for alias in mat.aliases:
            families[alias] = mat.family
            families[alias.upper()] = mat.family
    return families


def _load_partner_candidates(
    session: Session,
    owner_id: str,
    staleness_days: int,
    site_risk_by_partner: dict[str, int] | None = None,
) -> list[core_matching.PartnerCandidateInfo]:
    """Load all partner factories, their machines, relationships, checks, and live exposure."""
    partners = list(
        session.scalars(select(Factory).where(Factory.role == Role.PARTNER).order_by(Factory.id))
    )
    if not partners:
        return []

    partner_ids = [p.id for p in partners]

    # 1. Partner machines
    db_machines = list(
        session.scalars(select(Machine).where(Machine.factory_id.in_(partner_ids)).order_by(Machine.id))
    )
    machines_by_partner: dict[str, list[core_matching.PartnerMachineInfo]] = {}
    for m in db_machines:
        machines_by_partner.setdefault(m.factory_id, []).append(
            core_matching.PartnerMachineInfo(
                id=m.id,
                process=m.process,  # type: ignore[arg-type]
                tolerance_mm=m.achievable_tolerance_mm,
                envelope_mm=m.envelope_mm,
                available=m.available,
            )
        )

    # 2. Backup relationships
    rels = list(
        session.scalars(
            select(BackupRelationship).where(
                BackupRelationship.owner_id == owner_id,
                BackupRelationship.partner_id.in_(partner_ids),
            )
        )
    )
    rel_by_partner = {r.partner_id: r for r in rels}

    # 3. Relationship checks
    rel_ids = [r.id for r in rels]
    checks_by_rel: dict[str, list[CheckKey]] = {}
    if rel_ids:
        checks = list(
            session.scalars(
                select(RelationshipCheck).where(
                    RelationshipCheck.relationship_id.in_(rel_ids),
                    RelationshipCheck.done.is_(True),
                )
            )
        )
        for chk in checks:
            checks_by_rel.setdefault(chk.relationship_id, []).append(chk.key)

    # 4. Partner live risk: prefer the freshly computed exposure result passed in
    #    by find_matches_for_order; fall back to stored snapshots when absent.
    if site_risk_by_partner is None:
        site_risk_by_partner = {}
        snapshots = list(
            session.scalars(
                select(ExposureSnapshot).order_by(ExposureSnapshot.computed_at.desc())
            )
        )
        for snap in snapshots:
            if snap.result and "sites" in snap.result:
                for pid in partner_ids:
                    if pid not in site_risk_by_partner and pid in snap.result["sites"]:
                        site_risk_by_partner[pid] = snap.result["sites"][pid].get("site_risk", 0)

    # 5. Build PartnerCandidateInfo list
    now_utc = now()
    candidates: list[core_matching.PartnerCandidateInfo] = []

    for p in partners:
        rel = rel_by_partner.get(p.id)
        if rel is not None:
            status = rel.status
            eff_status = compute_effective_status(rel.status, rel.last_confirmed_at, now_utc, staleness_days)
            last_confirmed_days = (
                (now_utc - rel.last_confirmed_at).total_seconds() / 86400.0
                if rel.last_confirmed_at
                else None
            )
            completed_keys = tuple(checks_by_rel.get(rel.id, []))
        else:
            status = BackupStatus.POTENTIAL_MATCH
            eff_status = EffectiveStatus.POTENTIAL_MATCH
            last_confirmed_days = None
            completed_keys = ()

        candidates.append(
            core_matching.PartnerCandidateInfo(
                partner_id=p.id,
                name=p.name,
                lat=p.lat,
                lon=p.lon,
                cluster_id=p.cluster_id,
                hazard_zone_id=p.hazard_zone_id,
                grid_id=p.grid_id,
                shift_hours_per_day=p.shift_hours_per_day,
                materials_handled=tuple(p.materials_handled or []),
                typical_lead_time_hours=p.typical_lead_time_hours,
                mobilisation_hours=p.mobilisation_hours,
                spare_hours_per_week=dict(p.spare_hours_per_week or {}),
                machines=tuple(machines_by_partner.get(p.id, [])),
                status=status,
                effective_status=eff_status,
                last_confirmed_days_ago=last_confirmed_days,
                completed_check_keys=completed_keys,
                site_risk=site_risk_by_partner.get(p.id),
            )
        )

    return candidates


def find_matches_for_order(
    session: Session,
    order_id: str,
    scenario: dict[str, Any] | None = None,
) -> MatchingOut:
    """Find and rank backup partners for an order with correlated-risk awareness."""
    trace = TraceBuilder()
    now_utc = now()

    # Load order, part, and part steps
    order = session.get(Order, order_id)
    if order is None:
        raise AppError("NOT_FOUND", f"Order {order_id!r} not found.", status_code=404)

    part = session.get(Part, order.part_id)
    if part is None:
        raise AppError("NOT_FOUND", f"Part {order.part_id!r} not found.", status_code=404)

    owner_factory = session.get(Factory, order.factory_id)
    if owner_factory is None:
        raise AppError("NOT_FOUND", f"Factory {order.factory_id!r} not found.", status_code=404)

    steps_db = list(
        session.scalars(
            select(PartStep).where(PartStep.part_id == part.id).order_by(PartStep.seq)
        )
    )

    steps_match = tuple(
        core_matching.StepMatchRequirement(
            step_id=s.id,
            seq=s.seq,
            process=s.process,
            hours_per_unit=float(s.hours_per_unit),
            setup_hours=float(s.setup_hours),
            tolerance_mm=s.tolerance_mm,
            outsourced=s.outsourced,
        )
        for s in steps_db
    )

    due_diff_hours = max(0.0, (order.due_at - now_utc).total_seconds() / 3600.0)

    order_req = core_matching.OrderMatchRequirement(
        order_id=order.id,
        part_id=part.id,
        part_name=part.name,
        qty=order.qty,
        due_in_hours=due_diff_hours,
        material=part.material,
        steps=steps_match,
        envelope_mm=None,
    )

    trace.add(
        "load_order",
        f"Order {order.id} ({part.name}): qty={order.qty}, material={part.material}, "
        f"due in {due_diff_hours:.1f}h, {len(steps_match)} step(s).",
        inputs={"order_id": order.id, "part_id": part.id, "qty": order.qty, "due_at": order.due_at.isoformat()},
    )

    # Resolve scenario context
    hazard = HazardType.FLOOD
    affected_site_ids: tuple[str, ...] = ()

    if scenario:
        hazard_str = scenario.get("hazard")
        if hazard_str:
            try:
                hazard = HazardType(hazard_str)
            except ValueError:
                pass
        affected_site_ids = tuple(scenario.get("affected_sites") or ())

    context = core_matching.AffectedSiteContext(
        site_id=owner_factory.id,
        cluster_id=owner_factory.cluster_id,
        hazard_zone_id=owner_factory.hazard_zone_id,
        grid_id=owner_factory.grid_id,
        lat=owner_factory.lat,
        lon=owner_factory.lon,
        hazard=hazard,
        affected_site_ids=affected_site_ids,
    )

    # Configs
    configs = load_configs()
    matching_cfg = configs.matching
    readiness_cfg = configs.readiness
    material_families = _load_material_families()

    # Partner site risks: always computed fresh through the exposure service in
    # the current demo weather mode. This is idempotent (snapshots are keyed by
    # forecast hash) and keeps matching correct after a demo reset, when no
    # snapshots exist yet - without it every partner would silently carry
    # site_risk=None and the correlated-risk exclusion would never fire.
    exposure_result = exposure_service.compute_exposure(session, owner_factory.id)
    site_risk_by_partner = {
        site_id: item.site_risk
        for site_id, item in exposure_result.sites.items()
        if site_id != owner_factory.id
    }
    trace.add(
        "partner_exposure",
        f"Partner site risks from the exposure service ({exposure_result.mode} mode, "
        f"source={exposure_result.source}, degraded={exposure_result.degraded}).",
        inputs={"mode": exposure_result.mode},
        output={
            "site_risk_by_partner": site_risk_by_partner,
            "alert_threshold": configs.exposure.alert_threshold,
            "exclusion_rule": (
                "excluded when listed in the scenario's affected sites, or when site risk is at/above "
                "the alert threshold; the indicator is not a flood model, so threshold exclusions are "
                "the same evidence M4 alerts on"
            ),
        },
    )

    partners = _load_partner_candidates(
        session,
        owner_id=owner_factory.id,
        staleness_days=readiness_cfg.staleness_days,
        site_risk_by_partner=site_risk_by_partner,
    )

    trace.add(
        "candidates_loaded",
        f"Loaded {len(partners)} partner candidates for owner {owner_factory.id}.",
        output={"partner_ids": [p.partner_id for p in partners]},
    )

    # Run core matching algorithm
    result = core_matching.match_order_backups(
        order=order_req,
        context=context,
        partners=partners,
        material_families=material_families,
        status_weights=matching_cfg.status_weights,
        ranking_weights=matching_cfg.ranking_weights,
        stale_ready_weight=matching_cfg.stale_ready_weight,
        min_separation_km=matching_cfg.min_separation_km,
        alert_threshold=configs.exposure.alert_threshold,
        logistics_speed_kmh=matching_cfg.logistics_speed_kmh,
        logistics_base_hours=matching_cfg.logistics_base_hours,
        due_buffer_hours=configs.stress.due_buffer_hours,
        staleness_days=readiness_cfg.staleness_days,
        recommended_set_size=matching_cfg.recommended_set_size,
    )

    # Add trace steps
    for cand in result.candidates:
        if cand.excluded:
            trace.add(
                "candidate_excluded",
                f"Candidate {cand.name} excluded: {cand.exclusion_reason}.",
                output={"partner_id": cand.partner_id, "reason": cand.exclusion_reason},
            )
        elif cand.score is not None:
            trace.add(
                "candidate_ranked",
                f"Candidate {cand.name} scored {cand.score}/100 (effective status {cand.effective_status.value}).",
                output={"partner_id": cand.partner_id, "score": cand.score},
            )

    trace.add(
        "summary",
        f"Matching completed: fallback level is {result.fallback_level.value}; "
        f"best backup is {result.best_backup}.",
        output={
            "fallback_level": result.fallback_level.value,
            "best_backup": result.best_backup,
            "recommended_set": result.recommended_set.partner_ids if result.recommended_set else [],
        },
    )

    # Transform to schema
    candidates_out: list[CandidateOut] = []
    for c in result.candidates:
        filters_out = [
            FilterResult(
                key=f.key,
                result=f.result,  # type: ignore[arg-type]
                basis=f.basis,
                detail=f.detail,
            )
            for f in c.filters
        ]
        candidates_out.append(
            CandidateOut(
                partner_id=c.partner_id,
                name=c.name,
                status=c.status,
                effective_status=c.effective_status,
                distance_km=c.distance_km,
                filters=filters_out,
                unverified=list(c.unverified),
                excluded=c.excluded,
                exclusion_reason=c.exclusion_reason,
                flags=list(c.flags),
                score=c.score,
                selected_for_set=c.selected_for_set,
            )
        )

    rec_set_out: RecommendedSet | None = None
    if result.recommended_set is not None:
        rec_set_out = RecommendedSet(
            partner_ids=list(result.recommended_set.partner_ids),
            note=result.recommended_set.note,
        )

    return MatchingOut(
        order_id=order.id,
        candidates=candidates_out,
        recommended_set=rec_set_out,
        fallback_level=result.fallback_level,
        best_backup=result.best_backup,
        trace=[TraceEntry(**t) for t in trace.to_list()],
    )
