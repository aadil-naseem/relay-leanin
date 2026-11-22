"""M8 routers: readiness score, next-best actions, score history (section 8)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.readiness import ActionsOut, HistoryOut, ReadinessOut
from app.services import readiness as service

router = APIRouter(tags=["readiness"])


@router.get(
    "/readiness/{factory_id}",
    response_model=ReadinessOut,
    summary="Read recovery readiness for a time window",
)
def get_readiness(
    factory_id: str,
    window: int | None = Query(default=None),
    session: Session = Depends(get_db),
):
    return ReadinessOut.model_validate(service.readiness_out(session, factory_id, window))


@router.get(
    "/readiness/{factory_id}/actions",
    response_model=ActionsOut,
    summary="List next-best readiness actions",
)
def get_actions(
    factory_id: str,
    window: int | None = Query(default=None),
    session: Session = Depends(get_db),
):
    return ActionsOut.model_validate(service.actions_out(session, factory_id, window))


@router.get(
    "/readiness/{factory_id}/history",
    response_model=HistoryOut,
    summary="Read readiness score history",
)
def get_history(factory_id: str, session: Session = Depends(get_db)):
    return HistoryOut.model_validate(service.history_out(session, factory_id))
