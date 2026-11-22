"""M8 routers: backup relationships with effective status and guarded transitions."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.enums import CheckKey
from app.schemas.relationships import ReconfirmOut, RelationshipOut, StatusPatchIn
from app.services import relationships as service

router = APIRouter(tags=["relationships"])


def _out(relationship, session: Session) -> RelationshipOut:
    data = RelationshipOut.model_validate(relationship)
    data.effective_status = service.compute_effective_status(relationship)
    return data


@router.get(
    "/factories/{factory_id}/relationships",
    response_model=list[RelationshipOut],
    summary="List owner backup relationships and effective status",
)
def get_relationships(factory_id: str, session: Session = Depends(get_db)):
    return [_out(r, session) for r in service.list_relationships_for_owner(session, factory_id)]


@router.get(
    "/relationships/{relationship_id}",
    response_model=RelationshipOut,
    summary="Read a backup relationship",
)
def get_relationship(relationship_id: str, session: Session = Depends(get_db)):
    return _out(service.get_relationship(session, relationship_id), session)


@router.patch("/relationships/{relationship_id}/status", response_model=RelationshipOut)
def patch_status(relationship_id: str, payload: StatusPatchIn, session: Session = Depends(get_db)):
    # bad bodies become 422 VALIDATION_ERROR through the global handler;
    # missing checks become 409 MISSING_CHECKS from the service guard.
    return _out(service.patch_status(session, relationship_id, payload.status), session)


@router.post("/relationships/{relationship_id}/checks/{key}/complete", response_model=RelationshipOut)
def complete_check(relationship_id: str, key: CheckKey, session: Session = Depends(get_db)):
    return _out(service.complete_check(session, relationship_id, key), session)


@router.post("/relationships/{relationship_id}/reconfirm", response_model=ReconfirmOut)
def reconfirm(relationship_id: str, session: Session = Depends(get_db)):
    relationship = service.reconfirm(session, relationship_id)
    return ReconfirmOut(id=relationship.id, last_confirmed_at=relationship.last_confirmed_at)
