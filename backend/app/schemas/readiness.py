"""M8 readiness schemas: score, per-part breakdown, preparedness review, uplift actions."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.common import TraceEntry


class _Out(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WindowScore(_Out):
    window_hours: int
    score: float
    weighted_score: float


class PartCoverage(_Out):
    part_id: str
    part_name: str
    weight_inr: float
    covered: bool
    covered_by: str | None = None
    backup_status: str | None = None
    reason: str | None = None  # NO_PARTNER_ELIGIBLE | NOT_READY | STALE | CORRELATED | TOO_SLOW | NO_CAPACITY
    detail: str | None = None  # plain-word explanation for the UI


class ReviewItem(_Out):
    relationship_id: str
    partner_id: str
    partner_name: str
    status: str
    effective_status: str
    last_confirmed_at: datetime | None
    days_since_confirm: float | None
    expiring: bool = False
    action: str = "reconfirm"


class ReadinessOut(_Out):
    factory_id: str
    window_hours: int
    score: float
    weighted_score: float
    windows: list[WindowScore]
    breakdown: list[PartCoverage]
    review: list[ReviewItem]
    stale_partners: int = 0
    trace: list[TraceEntry] = []


class ActionOut(_Out):
    relationship_id: str
    partner_id: str
    label: str  # e.g. "Reconfirm Peenya partner"
    uplift_points: float
    current_score: float
    projected_score: float


class ActionsOut(_Out):
    factory_id: str
    window_hours: int
    actions: list[ActionOut]
    trace: list[TraceEntry] = []


class HistoryPoint(_Out):
    computed_at: datetime
    window_hours: int
    score: float
    weighted_score: float


class HistoryOut(_Out):
    factory_id: str
    points: list[HistoryPoint]