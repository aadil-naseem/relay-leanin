"""GET /api/v1/health - liveness + DB + weather mode + vision chain status (section 8)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.clock import now
from app.db import get_db
from app.settings import Settings, get_settings

router = APIRouter(tags=["health"])


def _provider_configured(provider: str, settings: Settings) -> bool:
    if provider == "cache":
        return True
    if provider == "gemini":
        return bool(settings.gemini_api_key and settings.gemini_model)
    if provider == "ollama":
        return bool(settings.ollama_model)
    return False


@router.get(
    "/health",
    summary="Check API, database and configured provider health",
)
def health(db: Session = Depends(get_db)) -> dict:
    settings = get_settings()
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:  # noqa: BLE001 - health must report, not raise
        db_status = "error"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "app_env": settings.app_env,
        "db": db_status,
        "weather_mode": settings.weather_mode,
        "vision_chain": [
            {"provider": provider, "configured": _provider_configured(provider, settings)}
            for provider in settings.vision_providers
        ],
        "time_utc": now().isoformat(),
    }
