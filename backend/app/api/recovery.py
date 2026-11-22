"""M7/M9/M10 routers: recovery request, handover pack, tracking stepper (section 8)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.recovery import (
    HandoverOut,
    RecoveryCreate,
    RecoveryOut,
    SelectPartnerIn,
    TrackingOut,
)
from app.services import recovery as service

router = APIRouter(tags=["recovery"])


@router.post(
    "/recovery-requests",
    response_model=RecoveryOut,
    status_code=201,
    summary="Create a sample recovery request",
)
def post_recovery_request(payload: RecoveryCreate, session: Session = Depends(get_db)):
    request = service.create_request(
        session,
        from_stress_test_id=payload.from_stress_test_id,
        order_id=payload.order_id,
        factory_id=payload.factory_id,
    )
    return RecoveryOut.model_validate(service.request_out(session, request))


@router.get("/recovery-requests/{request_id}", response_model=RecoveryOut)
def get_recovery_request(request_id: str, session: Session = Depends(get_db)):
    request = service._get_request(session, request_id)
    return RecoveryOut.model_validate(service.request_out(session, request))


@router.post(
    "/recovery-requests/{request_id}/select-partner",
    response_model=RecoveryOut,
    summary="Request activation with a selected backup partner",
)
def post_select_partner(request_id: str, payload: SelectPartnerIn, session: Session = Depends(get_db)):
    request = service.select_partner(session, request_id, payload.partner_id)
    return RecoveryOut.model_validate(service.request_out(session, request))


@router.get(
    "/recovery-requests/{request_id}/handover",
    response_model=HandoverOut,
    summary="Build the consent-aware handover pack",
)
def get_handover(request_id: str, session: Session = Depends(get_db)):
    return HandoverOut.model_validate(service.handover_out(session, request_id))


@router.get("/recovery-requests/{request_id}/tracking", response_model=TrackingOut)
def get_tracking(request_id: str, session: Session = Depends(get_db)):
    return TrackingOut.model_validate(service.tracking_out(session, request_id))


@router.post(
    "/recovery-requests/{request_id}/tracking/advance",
    response_model=TrackingOut,
    summary="Advance one simulated recovery milestone",
)
def post_tracking_advance(request_id: str, session: Session = Depends(get_db)):
    return TrackingOut.model_validate(service.advance_tracking(session, request_id))
