"""M2 passport schemas: wrapped fields with confidence, extraction report, RFQ view."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.enums import Confidence, PassportStatus
from app.schemas.common import TraceEntry


class _Out(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PassportField(_Out):
    """Every passport value carries its confidence and source (section 7.6)."""

    value: Any | None
    confidence: Confidence
    source: str | None = None  # rules | vision | cache | user
    candidates: list[Any] | None = None  # shown when sources disagree


class ExtractionMeta(_Out):
    provider: str | None = None  # cache | gemini | ollama | rules
    source: str | None = None
    latency_ms: int | None = None
    sha256: str | None = None
    degraded: bool = False
    warnings: list[str] = []


class ExtractResponse(_Out):
    passport_id: str
    status: PassportStatus
    data: dict[str, PassportField]
    extraction_meta: ExtractionMeta
    missing_required: list[str] = []  # fields that block confirm
    needs_review: list[str] = []  # fields where sources disagree or validation failed
    trace: list[TraceEntry] = []


class PassportOut(_Out):
    id: str
    part_id: str | None
    status: PassportStatus
    data: dict[str, PassportField]
    extraction_meta: ExtractionMeta
    source_sha256: str | None
    created_at: datetime
    updated_at: datetime


class PassportPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: dict[str, Any]  # edited fields become confidence=CONFIRMED (section 7.6 table)


class RedactionReport(_Out):
    removed_keys: list[str] = []
    scrubbed_text_fields: list[str] = []
    kept_keys: list[str] = []


class RfqOut(_Out):
    rfq_ref: str
    passport_id: str
    content: dict
    text: str
    redaction_report: RedactionReport
    deadline_days_from_now: int | None = None


class ShareIn(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {"partner_id": "fac_oragadam", "level": "RFQ"},
                {"partner_id": "fac_oragadam", "level": "FULL"},
            ]
        },
    )

    partner_id: str
    level: str = "RFQ"  # RFQ | FULL
