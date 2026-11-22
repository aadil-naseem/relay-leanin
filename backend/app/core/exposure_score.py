"""M4 exposure engine (blueprint section 7.2). Pure logic - no DB, no network.

Formulas implemented exactly as specified:

  max24  = max rolling 24 h precipitation sum in the horizon
  peak3  = max rolling 3 h sum
  H      = max(piecewise(max24, rain_24h_breakpoints), piecewise(peak3, rain_3h_breakpoints))
  V      = w_dep*D + w_wat*W + w_hist*Z
             D = clamp((ring_mean - elevation) / depression_full_m, 0, 1)
             W = 1 - clamp(nearest_water_m / water_full_distance_m, 0, 1)
             Z = 1 when the site is inside a curated historical-flood zone
  site_risk = round(100 * H * (floor + (1 - floor) * V))
  V_route   = clamp(w_low*low_share + w_under*min(underpasses, cap)/cap, 0, 1)
  route_risk = round(100 * H * (floor + (1 - floor) * V_route))

Honest labelling (R9): this is a risk *indicator* from forecast rain and site
conditions, not a flood model. Zones are curated planning circles from public
reporting, not official flood maps - the API labels this everywhere.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config_loader import ExposureConfig
from app.enums import RiskLevel


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def rolling_sums(series: list[float], window: int) -> list[float]:
    """Rolling window sums; position i = sum(series[i : i + window])."""
    if window <= 0 or len(series) < window:
        return []
    total = sum(series[:window])
    sums = [total]
    for index in range(window, len(series)):
        total += series[index] - series[index - window]
        sums.append(total)
    return sums


def max_rolling(series: list[float], window: int) -> float:
    sums = rolling_sums(series, window)
    return max(sums) if sums else 0.0


def piecewise(value: float, breakpoints: list[tuple[float, float]]) -> float:
    """Piecewise-linear interpolation, clamped at both ends."""
    if not breakpoints:
        return 0.0
    if value <= breakpoints[0][0]:
        return breakpoints[0][1]
    for (x0, y0), (x1, y1) in zip(breakpoints, breakpoints[1:]):
        if value <= x1:
            if x1 == x0:
                return y1
            return y0 + (value - x0) / (x1 - x0) * (y1 - y0)
    return breakpoints[-1][1]


@dataclass(frozen=True)
class RainHazard:
    max24_mm: float
    peak3_mm: float
    hazard_24: float
    hazard_3: float
    hazard: float  # H
    max24_window_start: int  # hour index where the worst 24 h window starts


def rain_hazard(series: list[float], cfg: ExposureConfig) -> RainHazard:
    window = min(24, len(series))
    sums24 = rolling_sums(series, window) if window else []
    max24 = max(sums24) if sums24 else 0.0
    start24 = sums24.index(max24) if sums24 else 0
    peak3 = max_rolling(series, 3)
    hazard_24 = piecewise(max24, cfg.rain_24h_breakpoints_mm)
    hazard_3 = piecewise(peak3, cfg.rain_3h_breakpoints_mm)
    return RainHazard(
        max24_mm=round(max24, 1),
        peak3_mm=round(peak3, 1),
        hazard_24=round(hazard_24, 4),
        hazard_3=round(hazard_3, 4),
        hazard=round(max(hazard_24, hazard_3), 4),
        max24_window_start=start24,
    )


@dataclass(frozen=True)
class Vulnerability:
    depression: float  # D
    water_proximity: float  # W
    flood_history: float  # Z
    value: float  # V
    relative_m: float
    nearest_water_m: float | None
    in_zone: bool


def vulnerability(
    *,
    elevation_m: float,
    ring_mean_m: float,
    nearest_water_m: float | None,
    zone_ids: list[str],
    cfg: ExposureConfig,
) -> Vulnerability:
    weights = cfg.vulnerability_weights
    depression = _clamp((ring_mean_m - elevation_m) / cfg.depression_full_m)
    if nearest_water_m is None:
        water = 0.0  # unknown water distance is treated as "no evidence", not as risk
    else:
        water = 1.0 - _clamp(nearest_water_m / cfg.water_full_distance_m)
    history = 1.0 if zone_ids else 0.0
    value = (
        weights.get("depression", 0.0) * depression
        + weights.get("water_proximity", 0.0) * water
        + weights.get("flood_history", 0.0) * history
    )
    return Vulnerability(
        depression=round(depression, 4),
        water_proximity=round(water, 4),
        flood_history=history,
        value=round(_clamp(value), 4),
        relative_m=round(elevation_m - ring_mean_m, 2),
        nearest_water_m=nearest_water_m,
        in_zone=bool(zone_ids),
    )


def site_risk(hazard: float, vuln: Vulnerability, cfg: ExposureConfig) -> int:
    """site_risk = round(100 * H * (floor + (1 - floor) * V))."""
    risk = 100.0 * hazard * (cfg.vulnerability_floor + (1.0 - cfg.vulnerability_floor) * vuln.value)
    return int(round(_clamp(risk, 0.0, 100.0)))


@dataclass(frozen=True)
class RouteFacts:
    route_id: str
    exit_id: str
    low_share: float | None = None
    underpass_count: int | None = None


def route_vulnerability(route: RouteFacts, cfg: ExposureConfig) -> float:
    if route.low_share is None:
        return 0.0  # no route facts -> no route-based evidence (section 3.4)
    weights = cfg.route_weights
    low = _clamp(route.low_share)
    cap = max(1, cfg.underpass_cap)
    underpasses = _clamp((route.underpass_count or 0) / cap)
    return _clamp(weights.get("low_share", 0.0) * low + weights.get("underpass", 0.0) * underpasses)


def route_risk(hazard: float, route: RouteFacts, cfg: ExposureConfig) -> int | None:
    if route.low_share is None:
        return None  # honest null: route facts unavailable, not "safe"
    v_route = route_vulnerability(route, cfg)
    risk = 100.0 * hazard * (cfg.vulnerability_floor + (1.0 - cfg.vulnerability_floor) * v_route)
    return int(round(_clamp(risk, 0.0, 100.0)))


def is_isolated(route_risks: list[int | None], cfg: ExposureConfig) -> bool:
    """All exits exposed: every route has facts and all of them are at/above threshold."""
    known = [risk for risk in route_risks if risk is not None]
    if not known or len(known) != len(route_risks):
        return False
    return all(risk >= cfg.alert_threshold for risk in known)


def onset_and_wet_spell(series: list[float], cfg: ExposureConfig) -> tuple[int | None, int]:
    """Onset = first hour whose rolling 3 h sum >= heavy_onset_mm_3h; spell capped."""
    thresholds = [
        index
        for index in range(max(0, len(series) - 2))
        if sum(series[index : index + 3]) >= cfg.heavy_onset_mm_3h
    ]
    if not thresholds:
        return None, 0
    onset = thresholds[0]
    spell = thresholds[-1] - onset + 1
    return onset, int(min(spell, cfg.wet_spell_cap_hours))


@dataclass(frozen=True)
class SiteExposure:
    site_id: str
    site_role: str
    site_risk: int
    risk_level: RiskLevel
    max24_mm: float
    peak3_mm: float
    hazard: float
    vulnerability: float
    onset_in_hours: int | None
    wet_spell_hours: int
    drivers: tuple[str, ...] = ()
    name: str = ""
    lat: float = 0.0
    lon: float = 0.0


def alert_affected(
    watched_site_ids: list[str],
    exposures: dict[str, "SiteExposure"],
    threshold: int,
) -> list[str]:
    """Sites (from the watched list) at or above the alert threshold, in order."""
    return [
        site_id
        for site_id in watched_site_ids
        if site_id in exposures and exposures[site_id].site_risk >= threshold
    ]


def explain_drivers(
    *,
    rain: RainHazard,
    vuln: Vulnerability,
    role: str,
    cfg: ExposureConfig,
) -> list[str]:
    """Plain-word drivers (section 7.2 "explainability")."""
    drivers: list[str] = []
    drivers.append(f"{rain.max24_mm:.0f} mm forecast in the heaviest 24 h (hazard {rain.hazard:.2f})")
    if rain.peak3_mm >= cfg.heavy_onset_mm_3h:
        drivers.append(f"{rain.peak3_mm:.0f} mm in the heaviest 3 h - cloudburst intensity")
    if vuln.depression >= 0.5:
        drivers.append(
            f"{abs(vuln.relative_m):.1f} m below the surrounding terrain"
            if vuln.relative_m < 0
            else f"{vuln.relative_m:+.1f} m relative elevation"
        )
    elif vuln.relative_m < 0:
        drivers.append(f"{abs(vuln.relative_m):.1f} m below the surrounding terrain")
    if vuln.nearest_water_m is not None and vuln.nearest_water_m <= cfg.water_full_distance_m / 2:
        drivers.append(f"{vuln.nearest_water_m:.0f} m from the nearest mapped water body")
    if vuln.in_zone:
        drivers.append("inside a curated historical-flood planning zone (not an official flood map)")
    if not drivers[1:] and vuln.value < 0.2:
        drivers.append("no terrain or water factors amplify the rain")
    return drivers