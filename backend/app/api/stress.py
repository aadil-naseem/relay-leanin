"""M5 stress test router (blueprint section 8): POST /stress-tests and GET /stress-tests/{id}."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.stress import StressCreate, StressOut
from app.services import stress as stress_service

router = APIRouter(prefix="/stress-tests", tags=["stress-tests"])


@router.post(
    "",
    response_model=StressOut,
    status_code=201,
    summary="Run a what-if production stress test",
)
def create_stress_test(
    body: StressCreate,
    db: Session = Depends(get_db),
) -> StressOut:
    """Run a manual what-if stress test given hazard, scope, start and duration."""
    return stress_service.run_manual_stress_test(db, body)


@router.get("/{test_id}", response_model=StressOut, summary="Read a stress-test result")
def get_stress_test(
    test_id: str,
    db: Session = Depends(get_db),
) -> StressOut:
    """Retrieve an existing stress test result by its ID."""
    return stress_service.get_stress_test(db, test_id)
