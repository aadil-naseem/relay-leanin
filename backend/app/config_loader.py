"""Loads every YAML in backend/config once into typed, validated objects.

All tuning constants live in YAML and are never hard-coded in logic (section 7).
Fail fast (R5 spirit): a missing key, wrong type, or contradictory weights raises
ConfigError naming the file, at startup - not mid-demo.
"""

from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"


class ConfigError(RuntimeError):
    def __init__(self, path: Path, cause: Exception | str) -> None:
        detail = cause if isinstance(cause, str) else str(cause).replace("\n", " ")
        super().__init__(f"Invalid config {path.name}: {detail}")


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------- exposure (7.2)

class ExposureConfig(_Strict):
    horizon_hours: int
    rain_24h_breakpoints_mm: list[tuple[float, float]]
    rain_3h_breakpoints_mm: list[tuple[float, float]]
    vulnerability_weights: dict[str, float]
    depression_full_m: float
    water_full_distance_m: float
    vulnerability_floor: float
    route_weights: dict[str, float]
    underpass_cap: int
    alert_threshold: int
    heavy_onset_mm_3h: float
    recession_hours: dict[str, int]
    wet_spell_cap_hours: int
    cache_ttl_minutes: int

    @model_validator(mode="after")
    def _sanity(self) -> "ExposureConfig":
        if not 0.0 <= self.vulnerability_floor <= 1.0:
            raise ValueError(f"vulnerability_floor must be within [0, 1], got {self.vulnerability_floor}")
        for name, weights in (("vulnerability_weights", self.vulnerability_weights), ("route_weights", self.route_weights)):
            total = sum(weights.values())
            if abs(total - 1.0) > 1e-6:
                raise ValueError(f"{name} must sum to 1.0, got {total}")
        for key in ("rain_24h_breakpoints_mm", "rain_3h_breakpoints_mm"):
            breakpoints = getattr(self, key)
            if not breakpoints or breakpoints[0][0] != 0:
                raise ValueError(f"{key} must start at 0 mm")
            millimetres = [mm for mm, _hazard in breakpoints]
            if millimetres != sorted(millimetres):
                raise ValueError(f"{key} millimetre thresholds must be ascending")
            hazards = [hazard for _mm, hazard in breakpoints]
            if any(h < 0 or h > 1 for h in hazards):
                raise ValueError(f"{key} hazards must be within [0, 1]")
        return self


# ---------------------------------------------------------------- stress (7.3)

class StressConfig(_Strict):
    due_buffer_hours: float
    transport_hours: float


# ---------------------------------------------------------------- matching (7.4)

class MatchingConfig(_Strict):
    min_separation_km: float
    logistics_speed_kmh: float
    logistics_base_hours: float
    recommended_set_size: int
    stale_ready_weight: float
    ranking_weights: dict[str, float]
    status_weights: dict[str, float]

    @model_validator(mode="after")
    def _sanity(self) -> "MatchingConfig":
        total = sum(self.ranking_weights.values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"ranking_weights must sum to 1.0, got {total}")
        if self.recommended_set_size < 1:
            raise ValueError("recommended_set_size must be at least 1")
        return self


# ---------------------------------------------------------------- readiness (7.5)

class ReadinessConfig(_Strict):
    staleness_days: int
    expiring_soon_days: int
    default_window_hours: int
    windows: list[int]
    min_separation_km: float

    @model_validator(mode="after")
    def _sanity(self) -> "ReadinessConfig":
        if self.default_window_hours not in self.windows:
            raise ValueError(f"default_window_hours {self.default_window_hours} must be one of windows {self.windows}")
        if sorted(self.windows) != self.windows:
            raise ValueError(f"windows must be ascending, got {self.windows}")
        return self


# ---------------------------------------------------------------- catalogues

class ProcessConfig(_Strict):
    default_hours_per_unit: float
    default_setup_hours: float
    water_dependent: bool = False
    vendor_batch: bool = False
    tolerance_range_mm: tuple[float, float] | None = None


class MaterialConfig(_Strict):
    grade: str
    family: str
    aliases: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------- cluster (9)

class ClusterSite(_Strict):
    id: str
    role: str
    name: str
    lat: float
    lon: float
    cluster_id: str
    hazard_zone_id: str | None = None
    grid_id: str | None = None
    note: str | None = None


class BacktestSite(_Strict):
    id: str
    name: str
    lat: float
    lon: float


class ExitJunction(_Strict):
    id: str
    name: str
    lat: float
    lon: float


class ReplayConfig(_Strict):
    event: str
    series_start_utc: datetime
    series_hours: int


class ClusterConfig(_Strict):
    name: str
    city: str
    note: str | None = None
    replay: ReplayConfig | None = None
    sites: list[ClusterSite] = Field(default_factory=list)
    backtest_flooded: list[BacktestSite] = Field(default_factory=list)
    backtest_not_flooded: list[BacktestSite] = Field(default_factory=list)
    exits: dict[str, list[ExitJunction]] = Field(default_factory=dict)


# ---------------------------------------------------------------- bundle

class ConfigBundle(_Strict):
    exposure: ExposureConfig
    stress: StressConfig
    matching: MatchingConfig
    readiness: ReadinessConfig
    processes: dict[str, ProcessConfig]
    materials: list[MaterialConfig]
    cluster: ClusterConfig


def _load_yaml(path: Path) -> Any:
    if not path.exists():
        raise ConfigError(path, "file is missing")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if data is None:
        raise ConfigError(path, "file is empty")
    return data


def _build(path: Path, model: type[BaseModel] | Any) -> Any:
    """Validate `model` against the YAML at `path`. Accepts classes and generic
    aliases (dict[str, X], list[X]); pydantic classes use model_validate, generic
    aliases need a TypeAdapter."""
    data = _load_yaml(path)
    try:
        if isinstance(model, type) and issubclass(model, BaseModel):
            return model.model_validate(data)
        return TypeAdapter(model).validate_python(data)
    except ConfigError:
        raise
    except Exception as exc:  # noqa: BLE001 - re-raised as ConfigError by design
        raise ConfigError(path, exc) from exc


@lru_cache(maxsize=1)
def load_configs(config_dir: str | None = None) -> ConfigBundle:
    directory = Path(config_dir) if config_dir else CONFIG_DIR
    return ConfigBundle(
        exposure=_build(directory / "exposure.yaml", ExposureConfig),
        stress=_build(directory / "stress.yaml", StressConfig),
        matching=_build(directory / "matching.yaml", MatchingConfig),
        readiness=_build(directory / "readiness.yaml", ReadinessConfig),
        processes=_build(directory / "processes.yaml", dict[str, ProcessConfig]),
        materials=_build(directory / "materials.yaml", list[MaterialConfig]),
        cluster=_build(directory / "cluster.yaml", ClusterConfig),
    )