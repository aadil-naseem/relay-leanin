"""Readiness snapshots: one row per computation, so the UI can plot the score moving (section 7.5)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import now
from app.db import Base, UTCDateTime


class ReadinessSnapshot(Base):
    __tablename__ = "readiness_snapshots"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    factory_id: Mapped[str] = mapped_column(String(64), index=True)
    window_hours: Mapped[int]
    score: Mapped[float]  # unweighted: covered critical parts / all critical parts
    weighted_score: Mapped[float]  # revenue-weighted
    breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    reason: Mapped[str | None] = mapped_column(String(200), default=None)
    computed_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: now())