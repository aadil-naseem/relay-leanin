"""Real-world exposure facts: curated hazard zones, per-site terrain, access routes (section 6).

All of this is prefetched in Phase 4 and committed with the repo (section 5), so
runtime never needs the internet for terrain or roads - only the forecast.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import now
from app.db import Base, UTCDateTime


class HazardZone(Base):
    """Curated historical-flood planning zone as a circle. NOT an official flood map (R9)."""

    __tablename__ = "hazard_zones"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    center_lat: Mapped[float]
    center_lon: Mapped[float]
    radius_m: Mapped[float]
    note: Mapped[str | None] = mapped_column(Text, default=None)  # cites the public reporting


class SiteTerrain(Base):
    """Terrain facts for a factory, vendor or supplier site."""

    __tablename__ = "site_terrain"

    site_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    elevation_m: Mapped[float]
    ring_mean_m: Mapped[float]  # mean elevation of the surrounding ring
    relative_m: Mapped[float]  # elevation_m - ring_mean_m (negative = in a depression)
    nearest_water_m: Mapped[float | None] = mapped_column(default=None)  # null when OSM water lookup found nothing
    zone_ids: Mapped[list] = mapped_column(JSON, default=list)  # membership derived at prefetch time
    source: Mapped[str] = mapped_column(String(64), default="open-meteo-elevation")
    fetched_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: now())


class Route(Base):
    """One access route (site -> exit junction), reduced to compact facts at prefetch."""

    __tablename__ = "routes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    site_id: Mapped[str] = mapped_column(String(64), index=True)
    exit_id: Mapped[str] = mapped_column(String(64))
    length_km: Mapped[float]
    samples: Mapped[list] = mapped_column(JSON, default=list)  # [{lat, lon, elevation_m}, ...]
    low_share: Mapped[float | None] = mapped_column(Float, default=None)  # share of samples below the 25th pct elevation
    underpass_count: Mapped[int] = mapped_column(default=0)  # OSM tunnel / negative-layer segments