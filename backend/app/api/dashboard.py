"""Dashboard (auto-run entry point) and the demo-reset control (sections 8, 8.1)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.demo_seed import reset_demo
from app.schemas.dashboard import DashboardOut, DemoStateOut
from app.services import dashboard as dashboard_service
from app.services import exposure as exposure_service
from app.settings import get_settings

router = APIRouter(tags=["dashboard"])


@router.get(
    "/dashboard/{factory_id}",
    response_model=DashboardOut,
    summary="Load the owner continuity dashboard",
    description="Computes replay/live exposure, auto-runs an idempotent alert stress test, and returns SPOFs and readiness.",
)
def get_dashboard(factory_id: str, session: Session = Depends(get_db)):
    return DashboardOut.model_validate(dashboard_service.dashboard_out(session, factory_id))


@router.post(
    "/demo/reset",
    response_model=DemoStateOut,
    summary="Reset the fictional sample world",
)
def post_demo_reset(session: Session = Depends(get_db)):
    """Rebuild the demo world from seed (section 8 Demo row; section 3.4 last-resort DB fallback)."""
    reset_demo()
    exposure_service.reset_weather_ttl()
    settings = get_settings()
    return DemoStateOut(
        weather_mode=settings.weather_mode,
        replay_event=settings.replay_event,
        data_label="SIMULATED SAMPLE",
    )
