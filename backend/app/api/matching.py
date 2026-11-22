"""M6 matching router (blueprint section 8): POST /matching/search."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.matching import MatchingOut, MatchRequest
from app.services import matching as matching_service

router = APIRouter(prefix="/matching", tags=["matching"])


@router.post(
    "/search",
    response_model=MatchingOut,
    summary="Find risk-aware backup partners for an order",
)
def search_matching_backups(
    body: MatchRequest,
    db: Session = Depends(get_db),
) -> MatchingOut:
    """Find and rank qualified backup partners for an order with correlated-risk awareness."""
    return matching_service.find_matches_for_order(db, body.order_id, scenario=body.scenario)
