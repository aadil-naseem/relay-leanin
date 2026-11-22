"""M6 risk-aware backup matching (blueprint section 7.4). Pure logic.

Implements:
  - Hard filters (process, material, tolerance, envelope, capacity, lead_time)
    returning PASS, FAIL, or UNKNOWN.
  - Requirement verification list (unverified checks that software cannot verify).
  - Correlated-risk exclusions:
      SAME_CLUSTER, SAME_HAZARD_ZONE, SAME_GRID (for power outage),
      ALSO_EXPOSED_SAME_EVENT (live forecast exposure in the same window).
  - Ranking score formula over viable non-excluded candidates:
      score = 100 * (0.40 * status_w + 0.20 * time_slack + 0.15 * capacity_slack + 0.15 * freshness + 0.10 * separation)
  - Greedy set selection (top-k) minimizing correlation among chosen partners.
  - Fallback level: READY (viable, fresh READY exists) | POTENTIAL_ONLY | NONE.

No database or FastAPI imports.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.geo import haversine_km
from app.enums import BackupStatus, CheckKey, EffectiveStatus, FallbackLevel, HazardType, ProcessCode

UNVERIFIED_CHECK_LABELS: dict[CheckKey, str] = {
    CheckKey.TECH_ASSESSMENT_DONE: "Technical assessment of machines and tolerances",
    CheckKey.SAMPLE_APPROVED: "First-article sample inspection and sign-off",
    CheckKey.TERMS_AGREED: "Commercial recovery terms and NDA",
    CheckKey.CAPACITY_RECONFIRMED: "Shop-floor capacity reconfirmation",
    CheckKey.CUSTOMER_APPROVED: "End-customer approval for alternative production",
}


@dataclass(frozen=True)
class StepMatchRequirement:
    step_id: str
    seq: int
    process: ProcessCode
    hours_per_unit: float
    setup_hours: float
    tolerance_mm: float | None = None
    envelope_mm: float | None = None
    outsourced: bool = False


@dataclass(frozen=True)
class OrderMatchRequirement:
    order_id: str
    part_id: str
    part_name: str
    qty: int
    due_in_hours: float
    material: str
    steps: tuple[StepMatchRequirement, ...] = ()
    envelope_mm: float | None = None


@dataclass(frozen=True)
class PartnerMachineInfo:
    id: str
    process: ProcessCode
    tolerance_mm: float | None = None
    envelope_mm: float | None = None
    available: bool = True


@dataclass(frozen=True)
class PartnerCandidateInfo:
    partner_id: str
    name: str
    lat: float
    lon: float
    cluster_id: str | None
    hazard_zone_id: str | None
    grid_id: str | None
    shift_hours_per_day: float
    materials_handled: tuple[str, ...]
    typical_lead_time_hours: float | None
    mobilisation_hours: float | None
    spare_hours_per_week: dict[str, float]
    machines: tuple[PartnerMachineInfo, ...]
    status: BackupStatus
    effective_status: EffectiveStatus
    last_confirmed_days_ago: float | None
    completed_check_keys: tuple[CheckKey, ...] = ()
    site_risk: int | None = None  # Live forecast exposure score


@dataclass(frozen=True)
class AffectedSiteContext:
    site_id: str
    cluster_id: str | None
    hazard_zone_id: str | None
    grid_id: str | None
    lat: float
    lon: float
    hazard: HazardType = HazardType.FLOOD
    affected_site_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class FilterEvaluation:
    key: str
    result: str  # PASS | FAIL | UNKNOWN
    basis: str
    detail: str


@dataclass(frozen=True)
class CandidateEvaluation:
    partner_id: str
    name: str
    status: BackupStatus
    effective_status: EffectiveStatus
    distance_km: float
    filters: tuple[FilterEvaluation, ...]
    unverified: tuple[str, ...]
    excluded: bool
    exclusion_reason: str | None
    flags: tuple[str, ...]
    score: float | None = None
    selected_for_set: bool = False


@dataclass(frozen=True)
class MatchSetResult:
    partner_ids: tuple[str, ...]
    note: str


@dataclass(frozen=True)
class MatchingResult:
    order_id: str
    candidates: tuple[CandidateEvaluation, ...]
    recommended_set: MatchSetResult | None
    fallback_level: FallbackLevel
    best_backup: str | None


def evaluate_hard_filters(
    order: OrderMatchRequirement,
    partner: PartnerCandidateInfo,
    distance_km: float,
    material_families: dict[str, str],
    logistics_speed_kmh: float = 35.0,
    logistics_base_hours: float = 4.0,
    due_buffer_hours: float = 24.0,
    staleness_days: int = 90,
) -> tuple[FilterEvaluation, ...]:
    """Run the 6 hard capability filters per section 7.4."""
    evals: list[FilterEvaluation] = []

    # 1. Process filter: Partner must have machines for every step process
    missing_procs: list[str] = []
    for step in order.steps:
        matching_machines = [
            m for m in partner.machines if m.available and m.process == step.process
        ]
        # For outsourced batch processes (like HEAT_TREAT), check if partner declared spare hours or handles it
        if not matching_machines:
            if step.outsourced and step.process.value in partner.spare_hours_per_week:
                continue
            missing_procs.append(step.process.value)

    if missing_procs:
        evals.append(
            FilterEvaluation(
                key="process",
                result="FAIL",
                basis="declared profile",
                detail=f"Partner lacks machine or capability for process(es): {', '.join(sorted(set(missing_procs)))}",
            )
        )
    else:
        evals.append(
            FilterEvaluation(
                key="process",
                result="PASS",
                basis="declared profile",
                detail="Partner possesses capable equipment or capabilities for all route steps.",
            )
        )

    # 2. Material filter: Partner handles the material or its family
    order_mat_norm = order.material.strip().upper()
    partner_mats = {m.strip().upper() for m in partner.materials_handled}
    mat_family = material_families.get(order.material, order.material)

    mat_match = False
    if order_mat_norm in partner_mats:
        mat_match = True
    else:
        # Check family overlap
        for pm in partner.materials_handled:
            if material_families.get(pm) == mat_family:
                mat_match = True
                break

    if mat_match:
        evals.append(
            FilterEvaluation(
                key="material",
                result="PASS",
                basis="declared profile (stock unverified)",
                detail=f"Partner handles {order.material} (family: {mat_family}).",
            )
        )
    else:
        evals.append(
            FilterEvaluation(
                key="material",
                result="FAIL",
                basis="declared profile (stock unverified)",
                detail=f"Partner declared profile does not list {order.material}.",
            )
        )

    # 3. Tolerance filter: tightest tolerances must be achievable
    tol_failures: list[str] = []
    for step in order.steps:
        if step.tolerance_mm is not None:
            capable_tol = [
                m
                for m in partner.machines
                if m.available
                and m.process == step.process
                and m.tolerance_mm is not None
                and m.tolerance_mm <= step.tolerance_mm
            ]
            if not capable_tol:
                tol_failures.append(f"{step.process.value} (requires ±{step.tolerance_mm} mm)")

    if tol_failures:
        evals.append(
            FilterEvaluation(
                key="tolerance",
                result="FAIL",
                basis="declared profile",
                detail=f"Partner machines cannot hold tolerance for: {', '.join(tol_failures)}",
            )
        )
    else:
        evals.append(
            FilterEvaluation(
                key="tolerance",
                result="PASS",
                basis="declared profile",
                detail="Partner achievable tolerances meet or exceed drawing requirements.",
            )
        )

    # 4. Envelope filter: part envelope must fit inside machine envelope
    part_env = order.envelope_mm
    if part_env is not None and part_env > 0:
        env_fits = all(
            any(
                m.envelope_mm is None or m.envelope_mm >= part_env
                for m in partner.machines
                if m.available and m.process == step.process
            )
            for step in order.steps
        )
        if env_fits:
            evals.append(
                FilterEvaluation(
                    key="envelope",
                    result="PASS",
                    basis="declared profile",
                    detail=f"Part envelope {part_env} mm fits partner working envelopes.",
                )
            )
        else:
            evals.append(
                FilterEvaluation(
                    key="envelope",
                    result="FAIL",
                    basis="declared profile",
                    detail=f"Part envelope {part_env} mm exceeds partner machine capacity.",
                )
            )
    else:
        evals.append(
            FilterEvaluation(
                key="envelope",
                result="PASS",
                basis="declared profile",
                detail="No dimension envelope restriction specified.",
            )
        )

    # 5. Capacity filter: spare capacity available in weekly horizon
    # UNKNOWN if last confirmed date is stale
    is_stale = (
        partner.effective_status == EffectiveStatus.STALE
        or (partner.last_confirmed_days_ago is not None and partner.last_confirmed_days_ago > staleness_days)
    )

    if is_stale:
        evals.append(
            FilterEvaluation(
                key="capacity",
                result="UNKNOWN",
                basis="declared capacity",
                detail="Capacity unverified because relationship confirmation is stale (> 90 days).",
            )
        )
    else:
        horizon_fraction = min(1.0, max(0.1, order.due_in_hours / 168.0))
        cap_failures: list[str] = []
        for step in order.steps:
            req_work = (order.qty * step.hours_per_unit) + step.setup_hours
            spare_hrs = partner.spare_hours_per_week.get(step.process.value, 0.0) * horizon_fraction
            if req_work > spare_hrs:
                cap_failures.append(
                    f"{step.process.value} requires {req_work:.1f}h, partner has {spare_hrs:.1f}h spare"
                )

        if cap_failures:
            evals.append(
                FilterEvaluation(
                    key="capacity",
                    result="FAIL",
                    basis="declared capacity",
                    detail=f"Insufficient spare capacity: {'; '.join(cap_failures)}",
                )
            )
        else:
            evals.append(
                FilterEvaluation(
                    key="capacity",
                    result="PASS",
                    basis="declared capacity",
                    detail="Declared spare capacity is sufficient for order batch size.",
                )
            )

    # 6. Lead time filter: mobilisation + production + logistics <= deadline - buffer
    mobilisation = partner.mobilisation_hours or 0.0
    logistics = (distance_km / max(1.0, logistics_speed_kmh)) + logistics_base_hours

    # Production time across steps
    shift_factor = 24.0 / max(1.0, partner.shift_hours_per_day)
    prod_hours = 0.0
    for step in order.steps:
        matching_count = max(
            1, len([m for m in partner.machines if m.available and m.process == step.process])
        )
        step_work = ((order.qty * step.hours_per_unit) + step.setup_hours) / matching_count
        prod_hours += step_work * shift_factor

    total_lead_time = mobilisation + prod_hours + logistics
    deadline_buffer = max(1.0, order.due_in_hours - due_buffer_hours)

    if total_lead_time <= deadline_buffer:
        evals.append(
            FilterEvaluation(
                key="lead_time",
                result="PASS",
                basis="declared lead time and distance",
                detail=f"Estimated completion in {total_lead_time:.1f}h (deadline buffer is {deadline_buffer:.1f}h).",
            )
        )
    else:
        evals.append(
            FilterEvaluation(
                key="lead_time",
                result="FAIL",
                basis="declared lead time and distance",
                detail=f"Estimated completion {total_lead_time:.1f}h exceeds deadline buffer {deadline_buffer:.1f}h.",
            )
        )

    return tuple(evals)


def evaluate_correlated_risk(
    partner: PartnerCandidateInfo,
    context: AffectedSiteContext,
    distance_km: float,
    min_separation_km: float = 10.0,
    alert_threshold: int = 50,
) -> tuple[bool, str | None, list[str]]:
    """Determine whether partner must be excluded for correlated disruption risk."""
    flags: list[str] = []

    if distance_km < min_separation_km:
        flags.append("NEARBY")

    if partner.effective_status == EffectiveStatus.STALE:
        flags.append("RECONFIRM_NEEDED")

    # 1. SAME_CLUSTER: Same industrial estate/cluster as disrupted site
    if partner.cluster_id and context.cluster_id and partner.cluster_id == context.cluster_id:
        return True, "SAME_CLUSTER", flags

    # 2. SAME_HAZARD_ZONE: Shares historical flood zone
    if partner.hazard_zone_id and context.hazard_zone_id and partner.hazard_zone_id == context.hazard_zone_id:
        return True, "SAME_HAZARD_ZONE", flags

    # 3. SAME_GRID: Same power grid during a power outage
    if context.hazard == HazardType.POWER_OUTAGE:
        if partner.grid_id and context.grid_id and partner.grid_id == context.grid_id:
            return True, "SAME_GRID", flags
    elif partner.grid_id and context.grid_id and partner.grid_id == context.grid_id:
        flags.append("SAME_GRID")

    # 4. ALSO_EXPOSED_SAME_EVENT: Partner itself is in the event storm footprint
    if partner.partner_id in context.affected_site_ids:
        return True, "ALSO_EXPOSED_SAME_EVENT", flags

    if partner.site_risk is not None and partner.site_risk >= alert_threshold:
        return True, "ALSO_EXPOSED_SAME_EVENT", flags

    # 5. Same exact site
    if partner.partner_id == context.site_id or distance_km < 1.0:
        return True, "NEARBY", flags

    return False, None, flags


def calculate_ranking_score(
    candidate: PartnerCandidateInfo,
    order: OrderMatchRequirement,
    distance_km: float,
    status_weights: dict[str, float],
    ranking_weights: dict[str, float],
    stale_ready_weight: float = 0.5,
    logistics_speed_kmh: float = 35.0,
    logistics_base_hours: float = 4.0,
    due_buffer_hours: float = 24.0,
    staleness_days: int = 90,
) -> float:
    """Calculate ranking score (0 to 100) for a viable non-excluded candidate."""
    # 1. Status weight
    if candidate.effective_status == EffectiveStatus.STALE:
        status_w = stale_ready_weight
    else:
        status_w = status_weights.get(candidate.status.value, 0.2)

    # 2. Time slack
    mobilisation = candidate.mobilisation_hours or 0.0
    logistics = (distance_km / max(1.0, logistics_speed_kmh)) + logistics_base_hours
    shift_factor = 24.0 / max(1.0, candidate.shift_hours_per_day)
    prod_hours = sum(
        (((order.qty * s.hours_per_unit) + s.setup_hours) / 1.0) * shift_factor for s in order.steps
    )
    total_time = mobilisation + prod_hours + logistics
    deadline = max(1.0, order.due_in_hours - due_buffer_hours)
    time_slack = min(1.0, max(0.0, (deadline - total_time) / deadline))

    # 3. Capacity slack
    spare_sum = sum(candidate.spare_hours_per_week.values()) if candidate.spare_hours_per_week else 0.0
    req_work_sum = sum((order.qty * s.hours_per_unit) + s.setup_hours for s in order.steps)
    cap_slack = min(1.0, max(0.0, spare_sum / max(1.0, req_work_sum * 2.0)))

    # 4. Freshness
    if candidate.last_confirmed_days_ago is None:
        freshness = 0.2
    else:
        freshness = min(1.0, max(0.0, 1.0 - (candidate.last_confirmed_days_ago / float(staleness_days))))

    # 5. Separation
    separation = min(1.0, max(0.0, distance_km / 100.0))

    score = 100.0 * (
        (ranking_weights.get("status", 0.40) * status_w)
        + (ranking_weights.get("time_slack", 0.20) * time_slack)
        + (ranking_weights.get("capacity_slack", 0.15) * cap_slack)
        + (ranking_weights.get("freshness", 0.15) * freshness)
        + (ranking_weights.get("separation", 0.10) * separation)
    )

    return round(score, 1)


def select_recommended_set(
    candidates: list[CandidateEvaluation],
    partner_map: dict[str, PartnerCandidateInfo],
    k: int = 2,
) -> tuple[tuple[str, ...], str] | None:
    """Greedy selection of top-k partners minimizing correlation among chosen partners."""
    viable = [c for c in candidates if not c.excluded and c.score is not None]
    if not viable:
        return None

    sorted_viable = sorted(viable, key=lambda c: c.score or 0.0, reverse=True)
    c1 = sorted_viable[0]
    p1 = partner_map[c1.partner_id]

    if len(sorted_viable) == 1 or k <= 1:
        note = f"Recommended partner {c1.name} ({c1.distance_km:.0f} km) is the primary qualified backup."
        return (c1.partner_id,), note

    # Pick c2 with highest diversity / minimal correlation with c1
    best_c2: CandidateEvaluation | None = None
    best_diversity_score = -float("inf")

    for cand in sorted_viable[1:]:
        p2 = partner_map[cand.partner_id]
        score = cand.score or 0.0
        penalty = 0.0

        if p2.cluster_id and p1.cluster_id and p2.cluster_id == p1.cluster_id:
            penalty += 20.0
        if p2.grid_id and p1.grid_id and p2.grid_id == p1.grid_id:
            penalty += 10.0
        if abs(cand.distance_km - c1.distance_km) < 15.0:
            penalty += 5.0

        adj_score = score - penalty
        if adj_score > best_diversity_score:
            best_diversity_score = adj_score
            best_c2 = cand

    assert best_c2 is not None
    p2 = partner_map[best_c2.partner_id]

    diff_grid = "independent power grids" if p1.grid_id != p2.grid_id else "regional grid"
    note = (
        f"Recommended set provides geographic separation across {c1.name} ({c1.distance_km:.0f} km) "
        f"and {best_c2.name} ({best_c2.distance_km:.0f} km) on {diff_grid}."
    )
    return (c1.partner_id, best_c2.partner_id), note


def match_order_backups(
    order: OrderMatchRequirement,
    context: AffectedSiteContext,
    partners: list[PartnerCandidateInfo],
    material_families: dict[str, str],
    status_weights: dict[str, float],
    ranking_weights: dict[str, float],
    stale_ready_weight: float = 0.5,
    min_separation_km: float = 10.0,
    alert_threshold: int = 50,
    logistics_speed_kmh: float = 35.0,
    logistics_base_hours: float = 4.0,
    due_buffer_hours: float = 24.0,
    staleness_days: int = 90,
    recommended_set_size: int = 2,
) -> MatchingResult:
    """Run full risk-aware backup matching pipeline for an order."""
    evaluations: list[CandidateEvaluation] = []
    partner_map: dict[str, PartnerCandidateInfo] = {p.partner_id: p for p in partners}

    for partner in partners:
        distance = round(haversine_km(context.lat, context.lon, partner.lat, partner.lon), 1)

        # 1. Hard filters
        filter_evals = evaluate_hard_filters(
            order=order,
            partner=partner,
            distance_km=distance,
            material_families=material_families,
            logistics_speed_kmh=logistics_speed_kmh,
            logistics_base_hours=logistics_base_hours,
            due_buffer_hours=due_buffer_hours,
            staleness_days=staleness_days,
        )

        all_passed = all(f.result in ("PASS", "UNKNOWN") for f in filter_evals)

        # 2. Correlated risk exclusions
        excluded, ex_reason, flags = evaluate_correlated_risk(
            partner=partner,
            context=context,
            distance_km=distance,
            min_separation_km=min_separation_km,
            alert_threshold=alert_threshold,
        )

        # 3. Unverified checks (requirements software cannot check)
        unverified_items: list[str] = []
        for key, label in UNVERIFIED_CHECK_LABELS.items():
            if key not in partner.completed_check_keys:
                unverified_items.append(f"{key.value}: {label}")

        # 4. Ranking score (only for viable and non-excluded candidates)
        score: float | None = None
        if all_passed and not excluded:
            score = calculate_ranking_score(
                candidate=partner,
                order=order,
                distance_km=distance,
                status_weights=status_weights,
                ranking_weights=ranking_weights,
                stale_ready_weight=stale_ready_weight,
                logistics_speed_kmh=logistics_speed_kmh,
                logistics_base_hours=logistics_base_hours,
                due_buffer_hours=due_buffer_hours,
                staleness_days=staleness_days,
            )

        evaluations.append(
            CandidateEvaluation(
                partner_id=partner.partner_id,
                name=partner.name,
                status=partner.status,
                effective_status=partner.effective_status,
                distance_km=distance,
                filters=filter_evals,
                unverified=tuple(unverified_items),
                excluded=excluded,
                exclusion_reason=ex_reason,
                flags=tuple(flags),
                score=score,
            )
        )

    # 5. Set selection
    set_selection = select_recommended_set(evaluations, partner_map, k=recommended_set_size)
    recommended_set: MatchSetResult | None = None
    selected_ids: set[str] = set()

    if set_selection is not None:
        p_ids, note = set_selection
        recommended_set = MatchSetResult(partner_ids=p_ids, note=note)
        selected_ids = set(p_ids)

    # Mark selected_for_set on candidate evaluations
    final_evals: list[CandidateEvaluation] = []
    for c in evaluations:
        final_evals.append(
            CandidateEvaluation(
                partner_id=c.partner_id,
                name=c.name,
                status=c.status,
                effective_status=c.effective_status,
                distance_km=c.distance_km,
                filters=c.filters,
                unverified=c.unverified,
                excluded=c.excluded,
                exclusion_reason=c.exclusion_reason,
                flags=c.flags,
                score=c.score,
                selected_for_set=c.partner_id in selected_ids,
            )
        )

    # Sort candidates: non-excluded by score desc, then excluded
    final_evals.sort(
        key=lambda c: (not c.excluded, c.score or 0.0, -c.distance_km),
        reverse=True,
    )

    # 6. Fallback level determination
    # READY if a viable, non-excluded, non-stale READY candidate exists
    # POTENTIAL_ONLY if any viable non-excluded candidate exists
    # NONE otherwise
    viable_non_excluded = [
        c
        for c in final_evals
        if not c.excluded and all(f.result in ("PASS", "UNKNOWN") for f in c.filters)
    ]

    has_ready = any(
        c.effective_status == EffectiveStatus.READY for c in viable_non_excluded
    )

    if has_ready:
        fallback_level = FallbackLevel.READY
        best_backup = next(
            c.partner_id for c in viable_non_excluded if c.effective_status == EffectiveStatus.READY
        )
    elif viable_non_excluded:
        fallback_level = FallbackLevel.POTENTIAL_ONLY
        best_backup = viable_non_excluded[0].partner_id
    else:
        fallback_level = FallbackLevel.NONE
        best_backup = None

    return MatchingResult(
        order_id=order.order_id,
        candidates=tuple(final_evals),
        recommended_set=recommended_set,
        fallback_level=fallback_level,
        best_backup=best_backup,
    )
