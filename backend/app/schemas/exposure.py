"""M4 exposure schemas: risk per site and route, drivers, alert object, map points."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.enums import RiskLevel
from app.schemas.common import TraceEntry


class _Out(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WeatherInfo(_Out):
    mode: str  # live | replay | synthetic
    source: str  # live | cache | replay | synthetic
    degraded: bool
    attribution: str = "Weather data by Open-Meteo.com"


class AlertOut(_Out):
    active: bool
    level: RiskLevel | None = None
    onset_in_hours: float | None = None
    max_24h_mm: float | None = None
    affected_sites: list[str] = []
    headline: str | None = None  # built by the stress step from its summary (section 7.2)


class SiteRisk(_Out):
    site_id: str
    site_role: str
    site_risk: int
    risk_level: RiskLevel
    max24_mm: float
    peak3_mm: float
    hazard: float
    vulnerability: float
    onset_in_hours: float | None = None
    wet_spell_hours: int | None = None
    isolation: bool = False
    drivers: list[str] = []


class RouteRiskOut(_Out):
    route_id: str
    exit_id: str
    route_risk: int | None = None  # null when route facts are unavailable (section 3.4)
    low_share: float | None = None
    underpass_count: int | None = None
    exposed: bool = False


class ExposureOut(_Out):
    factory_id: str
    computed_at: datetime
    weather: WeatherInfo
    site: SiteRisk
    routes: list[RouteRiskOut]
    alert: AlertOut | None
    trace: list[TraceEntry] = []


class MapPoint(_Out):
    site_id: str
    role: str
    name: str
    lat: float
    lon: float
    site_risk: int
    risk_level: RiskLevel
    isolation: bool = False


class ExposureMapOut(_Out):
    mode: str
    weather: WeatherInfo
    points: list[MapPoint]