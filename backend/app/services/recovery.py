"""M7/M9/M10 service: recovery request, ranked options, handover pack, stepper.

Honesty rules baked in (R9 + section 8.1):
- every payload carries `data_label: SIMULATED SAMPLE` for the mock parts;
- selecting a partner only SENDS a request - activation is subject to human,
  customer and contractual approvals outside the software (stated in the
  response and in the handover pack);
- the handover pack is consent-aware: identifying fields (part name, drawing
  number, customer alias) appear only when the selected partner holds FULL
  consent for the part's passport; otherwise the pack is redacted.

Options come from the M6 matcher run with the originating stress test's
scenario (hazard + affected sites), so exclusion reasons match the event.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config_loader import load_configs
from app.core.clock import now
from app.core.status_rules import effective_status as compute_effective_status
from app.enums import EffectiveStatus
from app.errors import AppError
from app.models import (
    BackupRelationship,
    Factory,
    Order,
    Part,
    Passport,
    PassportShare,
    RecoveryRequest,
    RecoveryStep,
    StressTest,
)
from app.services import matching as matching_service

DATA_LABEL = "SIMULATED SAMPLE"
ACTIVATION_NOTE = (
    "Selecting a partner sends a recovery request only. Activation is subject to "
    "human, customer and contractual approvals outside the software."
)

TRACKING_STEPS: tuple[str, ...] = (
    "REQUEST_SENT",
    "PARTNER_RESPONSE",
    "TECHNICAL_AND_CUSTOMER_APPROVALS",
    "PRODUCTION_SCHEDULED",
    "PRODUCTION_STARTED",
    "QUALITY_INSPECTION",
    "DISPATCH_AND_DELIVERY",
)

# Simulated milestone offsets from selection (hours). Clearly labelled simulated.
MILESTONE_OFFSETS_H: dict[str, float] = {
    "REQUEST_SENT": 0.0,
    "PARTNER_RESPONSE": 4.0,
    "TECHNICAL_AND_CUSTOMER_APPROVALS": 24.0,
    "PRODUCTION_SCHEDULED": 48.0,
    "PRODUCTION_STARTED": 72.0,
    "QUALITY_INSPECTION": 96.0,
    "DISPATCH_AND_DELIVERY": 120.0,
}

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
_jinja = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    undefined=StrictUndefined,
    autoescape=False,
)


def _get_request(session: Session, request_id: str) -> RecoveryRequest:
    request = session.get(RecoveryRequest, request_id)
    if request is None:
        raise AppError("NOT_FOUND", f"Recovery request {request_id!r} does not exist.", status_code=404)
    return request


def _load_stress(session: Session, stress_test_id: str) -> StressTest:
    stress = session.get(StressTest, stress_test_id)
    if stress is None:
        raise AppError("NOT_FOUND", f"Stress test {stress_test_id!r} does not exist.", status_code=404)
    return stress


def create_request(
    session: Session,
    *,
    from_stress_test_id: str | None = None,
    order_id: str | None = None,
    factory_id: str | None = None,
) -> RecoveryRequest:
    """Prefill from an alert (stress test + order) or create manually (factory + order)."""
    stress: StressTest | None = None
    if from_stress_test_id and order_id:
        stress = _load_stress(session, from_stress_test_id)
        factory_id = stress.factory_id
    elif not (factory_id and order_id):
        raise AppError(
            "VALIDATION_ERROR",
            "Provide from_stress_test_id together with order_id, or factory_id together with order_id.",
            status_code=422,
            details={"expected": {"prefill": ["from_stress_test_id", "order_id"], "manual": ["factory_id", "order_id"]}},
        )

    factory = session.get(Factory, factory_id)
    if factory is None:
        raise AppError("NOT_FOUND", f"Factory {factory_id!r} does not exist.", status_code=404)
    order = session.get(Order, order_id)
    if order is None:
        raise AppError("NOT_FOUND", f"Order {order_id!r} does not exist.", status_code=404)
    if order.factory_id != factory_id:
        raise AppError(
            "ORDER_NOT_IN_FACTORY",
            f"Order {order_id!r} belongs to {order.factory_id!r}, not {factory_id!r}.",
            status_code=409,
        )
    if stress is not None:
        order_ids = {o["order_id"] for o in (stress.result or {}).get("orders", [])}
        if order_ids and order_id not in order_ids:
            raise AppError(
                "ORDER_NOT_IN_STRESS_TEST",
                f"Order {order_id!r} is not part of stress test {from_stress_test_id!r}.",
                status_code=409,
            )

    part = session.get(Part, order.part_id)
    passport_id = part.passport_id if part else None

    request = RecoveryRequest(
        id=f"rr_{now().strftime('%Y%m%d%H%M%S')}_{order_id}",
        factory_id=factory_id,
        order_id=order_id,
        stress_test_id=from_stress_test_id,
        passport_id=passport_id,
        status="OPEN",
    )
    session.add(request)
    for step_key in TRACKING_STEPS:
        session.add(
            RecoveryStep(
                id=f"step_{request.id}_{step_key}",
                request_id=request.id,
                step_key=step_key,
                state="PENDING",
            )
        )
    session.commit()
    return request


def _scenario_for(session: Session, request: RecoveryRequest) -> dict | None:
    if not request.stress_test_id:
        return None
    stress = session.get(StressTest, request.stress_test_id)
    if stress is None:
        return None
    result = stress.result or {}
    return {
        "hazard": stress.params.get("hazard") or result.get("hazard"),
        "affected_sites": list(result.get("affected_sites") or []),
    }


def _outstanding_checks(session: Session, partner_id: str, owner_id: str) -> list[str]:
    relationship = session.scalars(
        select(BackupRelationship).where(
            BackupRelationship.owner_id == owner_id,
            BackupRelationship.partner_id == partner_id,
        )
    ).first()
    if relationship is None:
        return []
    staleness_days = load_configs().readiness.staleness_days
    effective = compute_effective_status(relationship.status, relationship.last_confirmed_at, now(), staleness_days)
    if effective == EffectiveStatus.STALE:
        return ["RECONFIRMATION pending (last confirmed beyond the staleness window)"]
    return [
        f"{check.key.value} pending"
        for check in relationship.checks
        if not check.done
    ]


def _capacity_summary(part: Part, partner: Factory) -> str:
    processes = sorted({step.process.value for step in part.steps})
    spare = partner.spare_hours_per_week or {}
    declared = [f"{name} {spare[name]:.0f} h/wk" for name in processes if name in spare]
    if not declared:
        return "no declared spare capacity for this route"
    return f"declared spare: {', '.join(declared)}"


def request_out(session: Session, request: RecoveryRequest) -> dict:
    order = session.get(Order, request.order_id)
    part = session.get(Part, order.part_id) if order else None
    scenario = _scenario_for(session, request)
    match = matching_service.find_matches_for_order(session, request.order_id, scenario=scenario)

    options = []
    for candidate in match.candidates:
        partner = session.get(Factory, candidate.partner_id)
        outstanding = _outstanding_checks(session, candidate.partner_id, request.factory_id)
        options.append(
            {
                "partner_id": candidate.partner_id,
                "name": candidate.name,
                "status": candidate.status.value,
                "effective_status": candidate.effective_status.value,
                "excluded": candidate.excluded,
                "exclusion_reason": candidate.exclusion_reason,
                "outstanding_checks": outstanding,
                "capacity_summary": _capacity_summary(part, partner) if part and partner else None,
            }
        )

    selected_outstanding = (
        _outstanding_checks(session, request.selected_partner_id, request.factory_id)
        if request.selected_partner_id
        else []
    )

    return {
        "id": request.id,
        "factory_id": request.factory_id,
        "order_id": request.order_id,
        "stress_test_id": request.stress_test_id,
        "passport_id": request.passport_id,
        "status": request.status,
        "selected_partner_id": request.selected_partner_id,
        "options": options,
        "outstanding_approvals": selected_outstanding,
        "data_label": DATA_LABEL,
        "activation_note": ACTIVATION_NOTE,
        "created_at": request.created_at,
    }


def select_partner(session: Session, request_id: str, partner_id: str) -> RecoveryRequest:
    """Record the selection and mark REQUEST_SENT. Excluded or incapable partners -> 409."""
    request = _get_request(session, request_id)
    partner = session.get(Factory, partner_id)
    if partner is None or partner.role.value != "PARTNER":
        raise AppError("NOT_FOUND", f"Partner {partner_id!r} does not exist.", status_code=404)

    scenario = _scenario_for(session, request)
    match = matching_service.find_matches_for_order(session, request.order_id, scenario=scenario)
    candidate = next((c for c in match.candidates if c.partner_id == partner_id), None)
    if candidate is None:
        raise AppError(
            "NOT_A_CANDIDATE",
            f"{partner_id!r} is not a candidate for order {request.order_id!r}.",
            status_code=409,
        )
    if candidate.excluded:
        raise AppError(
            "EXCLUDED_PARTNER",
            f"Cannot select {partner_id!r}: excluded for correlated risk ({candidate.exclusion_reason}).",
            status_code=409,
            details={"exclusion_reason": candidate.exclusion_reason},
        )
    failed = [f.key for f in candidate.filters if f.result == "FAIL"]
    if failed:
        raise AppError(
            "NOT_CAPABLE",
            f"Cannot select {partner_id!r}: hard filters failed ({', '.join(failed)}).",
            status_code=409,
            details={"failed_filters": failed},
        )

    if request.selected_partner_id == partner_id:
        return request  # idempotent re-selection
    if request.selected_partner_id is not None:
        raise AppError(
            "ALREADY_SELECTED",
            f"Request already selected {request.selected_partner_id!r}; reset the demo to start over.",
            status_code=409,
            details={"selected_partner_id": request.selected_partner_id},
        )

    request.selected_partner_id = partner_id
    request.status = "ACTIVE"
    sent = next(step for step in request.steps if step.step_key == "REQUEST_SENT")
    sent.state = "DONE"
    sent.at = now()
    session.commit()
    return request


def _consent_level(session: Session, request: RecoveryRequest) -> str | None:
    """RFQ | FULL | None - the passport share for the selected partner."""
    if not request.passport_id or not request.selected_partner_id:
        return None
    share = session.scalars(
        select(PassportShare).where(
            PassportShare.passport_id == request.passport_id,
            PassportShare.partner_id == request.selected_partner_id,
        )
    ).first()
    return share.level.value if share else None


def _checklist(part: Part) -> list[str]:
    items = [f"Material certificate (MTC) matching {part.material}"]
    tightest = [step.tolerance_mm for step in part.steps if step.tolerance_mm is not None]
    if tightest:
        items.append("First-article inspection before batch production")
        items.append(f"Hold dimensional tolerances to {min(tightest):.3f} mm on finished features")
    items.append("Final dimensional report with every dispatch")
    return items


def handover_out(session: Session, request_id: str) -> dict:
    """Mock handover pack, data-driven, rendered through Jinja2 (section 8 M9)."""
    request = _get_request(session, request_id)
    if not request.selected_partner_id:
        raise AppError(
            "NO_PARTNER_SELECTED",
            "Select a partner before generating the handover pack.",
            status_code=409,
        )
    order = session.get(Order, request.order_id)
    part = session.get(Part, order.part_id)
    partner = session.get(Factory, request.selected_partner_id)
    consent = _consent_level(session, request)

    full_consent = consent == "FULL"
    passport = session.get(Passport, request.passport_id) if request.passport_id else None
    rfq_ref = (passport.data or {}).get("rfq_ref", {}).get("value") if passport else None

    job_label = part.name if full_consent else f"Recovery job {request.id}"
    job_requirements: dict = {
        "job": job_label,
        "material": part.material,
        "process_route": [
            {"seq": step.seq, "process": step.process.value, "tolerance_mm": step.tolerance_mm}
            for step in sorted(part.steps, key=lambda s: s.seq)
        ],
        "tightest_tolerance_mm": min(
            (step.tolerance_mm for step in part.steps if step.tolerance_mm is not None), default=None
        ),
        "special_notes": [
            f"{step.process.value} step is outsourced by the owner"
            for step in part.steps
            if step.outsourced
        ],
    }

    authorised_documents: list[str] = ["Recovery request summary (this pack)"]
    if passport is not None and rfq_ref:
        authorised_documents.append(f"Redacted RFQ {rfq_ref}")
    if full_consent and passport is not None:
        authorised_documents = [
            f"Production passport {passport.id}",
            f"Drawing {part.drawing_no}",
            *(["Redacted RFQ " + rfq_ref] if rfq_ref else []),
        ]

    outstanding = _outstanding_checks(session, request.selected_partner_id, request.factory_id)
    required_approvals = list(outstanding) + ["Customer approval for alternate production source"]

    responsibilities = [
        {"party": f"Owner ({request.factory_id})", "responsibility": "Provide material, gauges and acceptance criteria"},
        {"party": f"Partner ({partner.name})", "responsibility": "Production, first-article inspection, dispatch"},
        {"party": "Both", "responsibility": ACTIVATION_NOTE},
    ]

    milestones = [
        {"step_key": key, "target_offset_hours": MILESTONE_OFFSETS_H[key]} for key in TRACKING_STEPS
    ]

    pack = {
        "request_id": request.id,
        "data_label": DATA_LABEL,
        "job_requirements": job_requirements,
        "authorised_documents": authorised_documents,
        "quantity": order.qty,
        "deadline": order.due_at,
        "inspection_checklist": _checklist(part),
        "responsibilities": responsibilities,
        "required_approvals": required_approvals,
        "milestones": milestones,
    }
    template = _jinja.get_template("handover.md.j2")
    pack["text"] = template.render(
        label=DATA_LABEL,
        job=job_label,
        material=part.material,
        route=job_requirements["process_route"],
        quantity=order.qty,
        deadline=order.due_at.strftime("%Y-%m-%d %H:%M UTC"),
        checklist=pack["inspection_checklist"],
        documents=authorised_documents,
        approvals=required_approvals,
        responsibilities=responsibilities,
        milestones=milestones,
        partner_name=partner.name,
        activation_note=ACTIVATION_NOTE,
        full_consent=full_consent,
    )
    return pack


def tracking_out(session: Session, request_id: str) -> dict:
    request = _get_request(session, request_id)
    steps = sorted(request.steps, key=lambda s: TRACKING_STEPS.index(s.step_key))
    return {
        "request_id": request.id,
        "data_label": DATA_LABEL,
        "steps": [{"step_key": s.step_key, "state": s.state, "at": s.at} for s in steps],
    }


def advance_tracking(session: Session, request_id: str) -> dict:
    """Move the simulated stepper forward by exactly one step."""
    request = _get_request(session, request_id)
    if not request.selected_partner_id:
        raise AppError(
            "NO_PARTNER_SELECTED",
            "Select a partner first; the stepper starts at REQUEST_SENT.",
            status_code=409,
        )
    steps = sorted(request.steps, key=lambda s: TRACKING_STEPS.index(s.step_key))
    pending = next((s for s in steps if s.state == "PENDING"), None)
    if pending is None:
        raise AppError(
            "ALL_STEPS_DONE",
            "The simulated recovery is complete; reset the demo to run it again.",
            status_code=409,
        )
    pending.state = "DONE"
    pending.at = now()
    session.commit()
    return tracking_out(session, request_id)
