"""M8 recovery readiness score (blueprint section 7.5). Pure logic.

A critical part is COVERED within window W when there exists a backup
relationship whose partner:

  1. is capable of the whole route: an available machine for every step
     (process match, achievable tolerance <= step tolerance, envelope fits)
     and the part material (or its family) is in the partner's handled list;
  2. is statically non-correlated with the owner: different cluster, hazard
     zone AND grid, and at least `min_separation_km` away;
  3. has an effective status of READY (a stale READY does not count);
  4. has declared spare capacity for every process in the route at the part's
     typical batch quantity:  qty*hpu + setup <= spare_hours_per_week[p] * W/168;
  5. can physically do it in time:  mobilisation + production + logistics <= W,
     with logistics = distance/35 + 4 and production summed per process as
     (batch_run_hours / n_machines + setup) * 24/shift_hours.

Uncovered reasons, in the order the ladder detects them (first hit wins):
  NO_PARTNER_ELIGIBLE - no partner is even capable of the route/material
  CORRELATED          - capable partners exist but all are statically correlated
  STALE               - the only non-correlated capable READY partner is stale
  NOT_READY           - non-correlated capable partners exist but none is READY
  NO_CAPACITY         - READY partners exist but declared spare capacity is insufficient
  TOO_SLOW            - READY partners with capacity exist but lead time > W

Scores: `score` (unweighted) = 100 * covered_parts / critical_parts;
`weighted_score` = 100 * sum(weight of covered) / sum(weight of critical),
where a part's weight is the total value of its open orders (fallback 1).
Coverage is monotone in W: a partner that covers at 24 h also covers at 72 h.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.geo import haversine_km
from app.enums import BackupStatus, EffectiveStatus, ProcessCode

REASON_NO_PARTNER_ELIGIBLE = "NO_PARTNER_ELIGIBLE"
REASON_CORRELATED = "CORRELATED"
REASON_STALE = "STALE"
REASON_NOT_READY = "NOT_READY"
REASON_NO_CAPACITY = "NO_CAPACITY"
REASON_TOO_SLOW = "TOO_SLOW"
COVERED = "COVERED"

WEEK_HOURS = 168.0
DEFAULT_LOGISTICS_SPEED_KMH = 35.0
DEFAULT_LOGISTICS_BASE_HOURS = 4.0


@dataclass(frozen=True)
class ReadinessStep:
    step_id: str
    seq: int
    process: ProcessCode
    hours_per_unit: float
    setup_hours: float
    tolerance_mm: float | None = None
    envelope_mm: float | None = None


@dataclass(frozen=True)
class ReadinessPart:
    part_id: str
    part_name: str
    material: str
    typical_batch_qty: int
    weight_inr: float
    steps: tuple[ReadinessStep, ...] = ()
    envelope_mm: float | None = None


@dataclass(frozen=True)
class ReadinessMachine:
    id: str
    process: ProcessCode
    tolerance_mm: float | None = None
    envelope_mm: float | None = None
    available: bool = True


@dataclass(frozen=True)
class ReadinessPartner:
    partner_id: str
    relationship_id: str | None
    name: str
    lat: float
    lon: float
    cluster_id: str
    hazard_zone_id: str | None
    grid_id: str | None
    shift_hours_per_day: float
    materials_handled: tuple[str, ...] = ()
    mobilisation_hours: float = 0.0
    spare_hours_per_week: dict[str, float] = field(default_factory=dict)
    machines: tuple[ReadinessMachine, ...] = ()
    status: BackupStatus = BackupStatus.POTENTIAL_MATCH
    effective_status: EffectiveStatus = EffectiveStatus.POTENTIAL_MATCH
    last_confirmed_days_ago: float | None = None


@dataclass(frozen=True)
class ReadinessOwner:
    factory_id: str
    lat: float
    lon: float
    cluster_id: str
    hazard_zone_id: str | None
    grid_id: str | None


@dataclass(frozen=True)
class PartCoverage:
    part_id: str
    part_name: str
    weight_inr: float
    covered: bool
    covered_by: str | None = None
    backup_status: str | None = None
    reason: str | None = None
    detail: str | None = None


@dataclass(frozen=True)
class WindowReadiness:
    window_hours: int
    score: float
    weighted_score: float
    covered_weight_inr: float
    total_weight_inr: float
    breakdown: tuple[PartCoverage, ...]


@dataclass(frozen=True)
class ReadinessResult:
    factory_id: str
    windows: tuple[WindowReadiness, ...]
    stale_partners: int


def material_ok(material: str, handled: tuple[str, ...], families: dict[str, str]) -> bool:
    """Material grade (or its family) is in the partner's handled list (section 7.4)."""
    if material in handled:
        return True
    part_family = families.get(material)
    if part_family is None:
        return False
    return any(families.get(grade) == part_family for grade in handled)


def _machines_for(partner: ReadinessPartner, process: ProcessCode) -> list[ReadinessMachine]:
    return [m for m in partner.machines if m.available and m.process == process]


def _step_servable(step: ReadinessStep, machine: ReadinessMachine) -> bool:
    if machine.process != step.process:
        return False
    if step.tolerance_mm is not None and machine.tolerance_mm is not None:
        if machine.tolerance_mm > step.tolerance_mm:
            return False
    if step.envelope_mm is not None and machine.envelope_mm is not None:
        if machine.envelope_mm < step.envelope_mm:
            return False
    return True


def is_correlated(partner: ReadinessPartner, owner: ReadinessOwner, distance_km: float, min_separation_km: float) -> bool:
    """Static non-correlation: different cluster, hazard zone, grid; >= min separation (section 7.5)."""
    if partner.cluster_id == owner.cluster_id:
        return True
    if partner.hazard_zone_id and owner.hazard_zone_id and partner.hazard_zone_id == owner.hazard_zone_id:
        return True
    if partner.grid_id and owner.grid_id and partner.grid_id == owner.grid_id:
        return True
    return distance_km < min_separation_km


def process_needs(part: ReadinessPart) -> dict[ProcessCode, tuple[float, float]]:
    """process -> (run_hours for the whole batch, setup_hours)."""
    run: dict[ProcessCode, float] = {}
    setups: dict[ProcessCode, float] = {}
    for step in part.steps:
        run[step.process] = run.get(step.process, 0.0) + step.hours_per_unit * part.typical_batch_qty
        setups[step.process] = setups.get(step.process, 0.0) + step.setup_hours
    return {process: (run[process], setups[process]) for process in run}


def capacity_ok(part: ReadinessPart, partner: ReadinessPartner, window_hours: int) -> bool:
    """Declared spare capacity covers every process at the typical batch quantity (section 7.4).

    Processes without a declared `spare_hours_per_week` entry have zero slack.
    """
    share_of_week = window_hours / WEEK_HOURS
    for process, (run_hours, setup_hours) in process_needs(part).items():
        spare = partner.spare_hours_per_week.get(process.value, 0.0)
        if run_hours + setup_hours > spare * share_of_week + 1e-9:
            return False
    return True


def lead_time_hours(
    part: ReadinessPart,
    partner: ReadinessPartner,
    distance_km: float,
    logistics_speed_kmh: float = DEFAULT_LOGISTICS_SPEED_KMH,
    logistics_base_hours: float = DEFAULT_LOGISTICS_BASE_HOURS,
) -> float:
    """Mobilisation + production + logistics (section 7.4 lead_time formula)."""
    shift_factor = 24.0 / partner.shift_hours_per_day if partner.shift_hours_per_day else 24.0
    production = 0.0
    for process, (run_hours, setup_hours) in process_needs(part).items():
        machines = _machines_for(partner, process)
        count = max(1, len(machines))
        production += (run_hours / count + setup_hours) * shift_factor
    logistics = distance_km / logistics_speed_kmh + logistics_base_hours
    return partner.mobilisation_hours + production + logistics


def capable(part: ReadinessPart, partner: ReadinessPartner, families: dict[str, str]) -> bool:
    """The partner can produce the whole route: material + a servable machine per step."""
    if not material_ok(part.material, partner.materials_handled, families):
        return False
    for step in part.steps:
        if not any(_step_servable(step, machine) for machine in _machines_for(partner, step.process)):
            return False
    return True


def coverage_for_window(
    parts: list[ReadinessPart],
    partners: list[ReadinessPartner],
    owner: ReadinessOwner,
    window_hours: int,
    *,
    min_separation_km: float,
    material_families: dict[str, str],
    logistics_speed_kmh: float = DEFAULT_LOGISTICS_SPEED_KMH,
    logistics_base_hours: float = DEFAULT_LOGISTICS_BASE_HOURS,
) -> list[PartCoverage]:
    """One coverage verdict per part, following the documented reason ladder."""
    out: list[PartCoverage] = []
    for part in parts:
        distance_by_partner = {
            partner.partner_id: haversine_km(owner.lat, owner.lon, partner.lat, partner.lon)
            for partner in partners
        }
        eligible = [p for p in partners if capable(part, p, material_families)]
        if not eligible:
            out.append(
                PartCoverage(
                    part_id=part.part_id, part_name=part.part_name, weight_inr=part.weight_inr,
                    covered=False, reason=REASON_NO_PARTNER_ELIGIBLE,
                    detail="no partner can serve every step of the route with the material",
                )
            )
            continue

        uncorrelated = [
            p for p in eligible
            if not is_correlated(p, owner, distance_by_partner[p.partner_id], min_separation_km)
        ]
        if not uncorrelated:
            names = ", ".join(sorted(p.name for p in eligible))
            out.append(
                PartCoverage(
                    part_id=part.part_id, part_name=part.part_name, weight_inr=part.weight_inr,
                    covered=False, reason=REASON_CORRELATED,
                    detail=f"capable partner(s) share the owner's cluster, zone, grid or are nearby: {names}",
                )
            )
            continue

        ready = [p for p in uncorrelated if p.effective_status == EffectiveStatus.READY]
        if not ready:
            stale = [p for p in uncorrelated if p.effective_status == EffectiveStatus.STALE]
            if stale:
                names = ", ".join(sorted(p.name for p in stale))
                out.append(
                    PartCoverage(
                        part_id=part.part_id, part_name=part.part_name, weight_inr=part.weight_inr,
                        covered=False, reason=REASON_STALE,
                        detail=f"READY partner(s) need reconfirmation: {names}",
                    )
                )
            else:
                names = ", ".join(sorted(p.name for p in uncorrelated))
                out.append(
                    PartCoverage(
                        part_id=part.part_id, part_name=part.part_name, weight_inr=part.weight_inr,
                        covered=False, reason=REASON_NOT_READY,
                        detail=f"capable partner(s) not READY yet: {names}",
                    )
                )
            continue

        with_capacity = [p for p in ready if capacity_ok(part, p, window_hours)]
        if not with_capacity:
            out.append(
                PartCoverage(
                    part_id=part.part_id, part_name=part.part_name, weight_inr=part.weight_inr,
                    covered=False, reason=REASON_NO_CAPACITY,
                    detail="READY partner(s) lack declared spare capacity for this batch in the window",
                )
            )
            continue

        timed = [
            (lead_time_hours(part, p, distance_by_partner[p.partner_id], logistics_speed_kmh, logistics_base_hours), p)
            for p in with_capacity
        ]
        best_lead, best = min(timed, key=lambda item: (item[0], item[1].partner_id))
        if best_lead > window_hours:
            out.append(
                PartCoverage(
                    part_id=part.part_id, part_name=part.part_name, weight_inr=part.weight_inr,
                    covered=False, reason=REASON_TOO_SLOW,
                    detail=f"fastest READY partner needs {best_lead:.1f} h (mobilisation + production + logistics)",
                )
            )
            continue

        out.append(
            PartCoverage(
                part_id=part.part_id, part_name=part.part_name, weight_inr=part.weight_inr,
                covered=True, covered_by=best.partner_id, backup_status=best.status.value,
                detail=f"{best.name} can run it in {best_lead:.1f} h (window {window_hours} h)",
            )
        )
    return out


def window_score(parts: list[ReadinessPart], coverage: list[PartCoverage]) -> tuple[float, float, float, float]:
    """(unweighted, weighted, covered_weight, total_weight) for one window."""
    total_weight = sum(part.weight_inr for part in parts)
    covered_by_id = {item.part_id for item in coverage if item.covered}
    covered_weight = sum(part.weight_inr for part in parts if part.part_id in covered_by_id)
    if not parts:
        return 0.0, 0.0, 0.0, 0.0
    unweighted = 100.0 * len(covered_by_id) / len(parts)
    weighted = 100.0 * covered_weight / total_weight if total_weight > 0 else 0.0
    return round(unweighted, 1), round(weighted, 1), covered_weight, total_weight


def compute_readiness(
    parts: list[ReadinessPart],
    partners: list[ReadinessPartner],
    owner: ReadinessOwner,
    windows: list[int],
    *,
    min_separation_km: float,
    material_families: dict[str, str],
    logistics_speed_kmh: float = DEFAULT_LOGISTICS_SPEED_KMH,
    logistics_base_hours: float = DEFAULT_LOGISTICS_BASE_HOURS,
) -> ReadinessResult:
    """Full readiness: per-window scores plus breakdowns (section 7.5)."""
    stale_partners = sum(1 for p in partners if p.effective_status == EffectiveStatus.STALE)
    results: list[WindowReadiness] = []
    for window in sorted(windows):
        coverage = coverage_for_window(
            parts, partners, owner, window,
            min_separation_km=min_separation_km,
            material_families=material_families,
            logistics_speed_kmh=logistics_speed_kmh,
            logistics_base_hours=logistics_base_hours,
        )
        unweighted, weighted, covered_weight, total_weight = window_score(parts, coverage)
        results.append(
            WindowReadiness(
                window_hours=window,
                score=unweighted,
                weighted_score=weighted,
                covered_weight_inr=covered_weight,
                total_weight_inr=total_weight,
                breakdown=tuple(coverage),
            )
        )
    return ReadinessResult(factory_id=owner.factory_id, windows=tuple(results), stale_partners=stale_partners)


@dataclass(frozen=True)
class PartnerReview:
    relationship_id: str
    partner_id: str
    partner_name: str
    status: str
    effective_status: str
    days_since_confirm: float | None
    expiring: bool


def review_partners(
    partners: list[ReadinessPartner],
    staleness_days: float,
    expiring_soon_days: float,
) -> list[PartnerReview]:
    """Preparedness review: stale partners and READY partners expiring soon (section 7.5).

    A READY relationship is `expiring` when its confirmation age is within
    `expiring_soon_days` of the staleness window (status_rules.is_expiring_soon).
    """
    items: list[PartnerReview] = []
    for partner in partners:
        if partner.relationship_id is None:
            continue
        if partner.effective_status not in (EffectiveStatus.STALE, EffectiveStatus.READY):
            continue
        age = partner.last_confirmed_days_ago
        expiring = False
        if (
            partner.effective_status == EffectiveStatus.READY
            and age is not None
            and age >= staleness_days - expiring_soon_days
        ):
            expiring = True
        items.append(
            PartnerReview(
                relationship_id=partner.relationship_id,
                partner_id=partner.partner_id,
                partner_name=partner.name,
                status=partner.status.value,
                effective_status=partner.effective_status.value,
                days_since_confirm=round(age, 1) if age is not None else None,
                expiring=expiring,
            )
        )
    return items
