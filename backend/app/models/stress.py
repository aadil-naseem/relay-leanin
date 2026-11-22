"""Exposure snapshots and stress tests - stored results of computed modules (section 6).

exposure_snapshots.result and stress_tests.result keep the full JSON payloads so
the UI can re-render any past computation, and the trace stays auditable.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import now
from app.db import Base, UTCDateTime
from app.enums import Trigger


class ExposureSnapshot(Base):
    __tablename__ = "exposure_snapshots"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    factory_id: Mapped[str] = mapped_column(String(64), index=True)
    mode: Mapped[str] = mapped_column(String(16))  # live | replay | synthetic
    computed_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: now())
    forecast_hash: Mapped[str] = mapped_column(String(64))
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    alert: Mapped[bool] = mapped_column(Boolean, default=False)


class StressTest(Base):
    __tablename__ = "stress_tests"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    trigger: Mapped[Trigger] = mapped_column(SAEnum(Trigger, native_enum=False))
    factory_id: Mapped[str] = mapped_column(String(64), index=True)
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    exposure_snapshot_id: Mapped[str | None] = mapped_column(String(64), default=None)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: now())