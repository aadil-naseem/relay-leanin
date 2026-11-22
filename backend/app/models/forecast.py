"""Forecast cache - fallback 1 of the degradation ladder (sections 3.4, 6)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import now
from app.db import Base, UTCDateTime


class ForecastCache(Base):
    """Last good forecast per cache key."""

    __tablename__ = "forecast_cache"

    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    fetched_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: now())
    source: Mapped[str] = mapped_column(String(32), default="open-meteo")