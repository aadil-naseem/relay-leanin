"""M6 matching schemas: candidates with checked/unverified requirements, exclusions, ranking."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.enums import BackupStatus, EffectiveStatus, FallbackLevel
from app.schemas.common import TraceEntry


class _Out(BaseModel):
    model_config = ConfigDict(extra="forbid")


FilterVerdict = Literal["PASS", "FAIL", "UNKNOWN"]


class FilterResult(_Out):
    key: str  # process | material | tolerance | envelope | capacity | lead_time
    result: FilterVerdict
    basis: str  # declared profile | scenario
    detail: str


class CandidateOut(_Out):
    partner_id: str
    name: str
    status: BackupStatus
    effective_status: EffectiveStatus
    distance_km: float
    filters: list[FilterResult] = []
    unverified: list[str] = []  # requirements software cannot check, with the closing check
    excluded: bool = False
    exclusion_reason: str | None = None  # SAME_CLUSTER | SAME_HAZARD_ZONE | SAME_GRID | ALSO_EXPOSED_SAME_EVENT | NEARBY
    flags: list[str] = []
    score: float | None = None  # only for viable, non-excluded candidates
    selected_for_set: bool = False


class RecommendedSet(_Out):
    partner_ids: list[str]
    note: str  # set_correlation_note


class MatchRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {"order_id": "ord_102"},
                {
                    "order_id": "ord_102",
                    "scenario": {"hazard": "FLOOD", "affected_sites": ["fac_owner", "ven_heat"]},
                },
            ]
        },
    )

    order_id: str
    scenario: dict | None = None  # optional scenario override from a stress test


class MatchingOut(_Out):
    order_id: str
    candidates: list[CandidateOut]
    recommended_set: RecommendedSet | None = None
    fallback_level: FallbackLevel
    best_backup: str | None = None
    trace: list[TraceEntry] = []
