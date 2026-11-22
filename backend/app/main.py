"""FastAPI application: CORS, /api/v1 router, error handlers, health."""

from __future__ import annotations

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    dashboard,
    exposure,
    factories,
    health,
    matching,
    passports,
    readiness,
    recovery,
    relationships,
    spof,
    stress,
)
from app.errors import register_error_handlers
from app.settings import get_settings

API_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Factory Continuity Desk (Relay) API",
        version="0.1.0",
        description=(
            "Finds where a factory would break before a disruption, and shows who could cover the work. "
            "Demo data is sample / simulated; weather, terrain and road data are real."
        ),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)

    api = APIRouter(prefix=API_PREFIX)
    api.include_router(health.router)
    api.include_router(factories.router)
    api.include_router(relationships.router)
    api.include_router(spof.router)
    api.include_router(exposure.router)
    api.include_router(stress.router)
    api.include_router(matching.router)
    api.include_router(readiness.router)
    api.include_router(recovery.router)
    api.include_router(passports.router)
    api.include_router(dashboard.router)
    app.include_router(api)
    return app


app = create_app()