"""M5 what-if schemas: request with scope, per-order impact, summary, headline."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.enums import FallbackLevel, HazardType, OrderState, Trigger
from app.schemas.common import TraceEntry


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _Out(BaseModel):
    model_config = ConfigDict(extra="forbid")


ScopeType = Literal["zone", "cluster", "grid", "sites", "exposure_alert", "resource"]


class ScopeIn(_In):
    type: ScopeType
    ids: list[str] = []


class StressCreate(_In):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "factory_id": "fac_owner",
                    "hazard": "FLOOD",
                    "scope": {"type": "exposure_alert", "ids": ["fac_owner", "ven_heat"]},
                    "start_in_hours": 24,
                    "duration_hours": 72,
                }
            ]
        },
    )

    factory_id: str
    hazard: HazardType
    scope: ScopeIn
    start_in_hours: float = Field(ge=0)
    duration_hours: float = Field(gt=0)


class OrderImpact(_Out):
    order_id: str
    part_id: str
    state: OrderState
    due_at: datetime
    stressed_finish_at: datetime
    baseline_finish_at: datetime
    days_late: float | None = None
    value_inr: float
    fallback_level: FallbackLevel
    best_backup: str | None = None


class StressSummary(_Out):
    orders_at_risk: int
    revenue_exposed_inr: float
    orders_no_fallback: int
    orders_no_ready_fallback: int


class StressOut(_Out):
    id: str
    trigger: Trigger
    hazard: HazardType
    factory_id: str
    affected_sites: list[str]
    orders: list[OrderImpact]
    summary: StressSummary
    headline: str
    params: dict
    exposure_snapshot_id: str | None = None
    created_at: datetime
    trace: list[TraceEntry] = []
