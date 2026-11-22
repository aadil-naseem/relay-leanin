"""Dashboard (auto-run entry point, section 8.1) and demo-control schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.enums import Role
from app.schemas.exposure import WeatherInfo
from app.schemas.spof import SpofItem


class _Out(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DashboardFactory(_Out):
    id: str
    name: str
    role: Role
    cluster_id: str
    hazard_zone_id: str | None
    grid_id: str | None


class DashboardReadinessHeadline(_Out):
    window: int
    score: float
    weighted: float


class DashboardReadiness(_Out):
    headline: DashboardReadinessHeadline
    windows: dict[str, float]  # {"24": .., "48": .., "72": ..}


class DashboardAlert(_Out):
    active: bool
    headline: str | None = None
    onset_in_hours: float | None = None
    stress_test_id: str | None = None
    cta: str | None = None  # "START_RECOVERY" when there is something to act on


class DashboardOut(_Out):
    factory: DashboardFactory
    data_label: str = "SIMULATED SAMPLE"
    weather: WeatherInfo
    readiness: DashboardReadiness
    alert: DashboardAlert
    spof_top: list[SpofItem]
    exposure_summary: dict
    stale_partners: int


class DemoModeIn(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"weather": "replay"}, {"weather": "synthetic"}]},
    )

    weather: str  # live | replay | synthetic


class DemoStateOut(_Out):
    weather_mode: str
    replay_event: str
    data_label: str = "SIMULATED SAMPLE"
