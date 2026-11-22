"""Weather adapter: hourly precipitation with the section 3.4 degradation ladder.

  live  -> Open-Meteo forecast (batched multi-location, one call)
  cache -> last good forecast per site from `forecast_cache`
  replay-> real Cyclone Michaung rain (Dec 2023), time-shifted so index 0 = now
  synthetic -> generated profile, clearly labelled SYNTHETIC SAMPLE

Every result carries `source` and `degraded`, and the API surfaces both so the
UI can say "showing the last good forecast" or "replay of Dec-2023 rain".

Verified live 2026-11-14 (docs/VERIFIED_FACTS.md): multi-location forecast
returns an ARRAY of per-location objects; `forecast_days=4` gives 96 hourly
values from 00:00 UTC today, so slicing from the current hour leaves enough
for a 72 h horizon.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from app.core.clock import now
from app.models import ForecastCache

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "cache"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
HORIZON_HOURS = 72
FORECAST_DAYS = 4  # 96 h from 00:00 UTC -> enough to slice a full horizon from "now"
HTTP_TIMEOUT_S = 20.0
LIVE = "live"
CACHE = "cache"
REPLAY = "replay"
SYNTHETIC = "synthetic"


@dataclass(frozen=True)
class SiteSpec:
    site_id: str
    lat: float
    lon: float


@dataclass(frozen=True)
class SiteSeries:
    site_id: str
    lat: float
    lon: float
    series: tuple[float, ...]
    source: str  # live | cache | replay | synthetic
    degraded: bool  # True when the requested mode was not available


@dataclass(frozen=True)
class WeatherResult:
    mode: str
    source: str  # overall: live | cache | replay | synthetic
    degraded: bool
    sites: dict[str, SiteSeries]
    attribution: str = "Weather data by Open-Meteo.com"

    def series(self, site_id: str) -> tuple[float, ...]:
        return self.sites[site_id].series


def _cache_key(site: SiteSpec) -> str:
    return f"forecast:{site.site_id}:{site.lat:.4f}:{site.lon:.4f}"


def _fetch_live(sites: list[SiteSpec]) -> dict[str, tuple[float, ...]]:
    """One batched Open-Meteo call; returns site_id -> 72 hourly mm from now."""
    lats = ",".join(f"{site.lat:.4f}" for site in sites)
    lons = ",".join(f"{site.lon:.4f}" for site in sites)
    params = {
        "latitude": lats,
        "longitude": lons,
        "hourly": "precipitation",
        "forecast_days": FORECAST_DAYS,
        "timezone": "UTC",
    }
    with httpx.Client(timeout=HTTP_TIMEOUT_S) as client:
        response = client.get(FORECAST_URL, params=params)
        response.raise_for_status()
        payload = response.json()

    entries = payload if isinstance(payload, list) else [payload]
    if len(entries) != len(sites):
        raise ValueError(f"forecast returned {len(entries)} locations for {len(sites)} sites")

    current_hour = now().astimezone(timezone.utc).strftime("%Y-%m-%dT%H:00")
    out: dict[str, tuple[float, ...]] = {}
    for site, entry in zip(sites, entries):
        hourly = entry.get("hourly") or {}
        times: list[str] = hourly.get("time") or []
        values: list[float | None] = hourly.get("precipitation") or []
        if not times or len(times) != len(values):
            raise ValueError(f"forecast hourly payload malformed for {site.site_id}")
        start = times.index(current_hour) if current_hour in times else 0
        series = [float(v) if v is not None else 0.0 for v in values[start : start + HORIZON_HOURS]]
        if len(series) < HORIZON_HOURS:
            raise ValueError(f"forecast horizon short for {site.site_id}: {len(series)} h")
        out[site.site_id] = tuple(series)
    return out


def _read_cached(session: Session, sites: list[SiteSpec]) -> dict[str, tuple[float, ...]]:
    out: dict[str, tuple[float, ...]] = {}
    for site in sites:
        row = session.get(ForecastCache, _cache_key(site))
        if row is None:
            continue
        series = (row.payload or {}).get("series") or []
        if len(series) >= HORIZON_HOURS:
            out[site.site_id] = tuple(float(v) for v in series[:HORIZON_HOURS])
    return out


def _store_cache(session: Session, sites: list[SiteSpec], fetched: dict[str, tuple[float, ...]]) -> None:
    stamp = now()
    for site in sites:
        series = fetched.get(site.site_id)
        if not series:
            continue
        row = session.get(ForecastCache, _cache_key(site))
        payload = {"series": list(series), "lat": site.lat, "lon": site.lon}
        if row is None:
            session.add(ForecastCache(key=_cache_key(site), payload=payload, fetched_at=stamp, source="open-meteo"))
        else:
            row.payload = payload
            row.fetched_at = stamp
            row.source = "open-meteo"
    session.commit()


def _load_file_series(name: str, sites: list[SiteSpec]) -> dict[str, tuple[float, ...]]:
    path = CACHE_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"{path} is part of the committed prefetch cache (Phase 4)")
    payload = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, tuple[float, ...]] = {}
    for site in sites:
        entry = (payload.get("sites") or {}).get(site.site_id)
        if entry is None:
            continue
        series = entry.get("precipitation_mm") or []
        out[site.site_id] = tuple(float(v) for v in series[:HORIZON_HOURS])
    return out


def _fill_missing_zeros(series: dict[str, tuple[float, ...]], sites: list[SiteSpec]) -> dict[str, tuple[float, ...]]:
    for site in sites:
        if site.site_id not in series:
            logger.warning("no precipitation series for %s; using zeros", site.site_id)
            series[site.site_id] = tuple(0.0 for _ in range(HORIZON_HOURS))
    return series


def get_hourly_precip(
    session: Session,
    sites: list[SiteSpec],
    mode: str,
    horizon_hours: int = HORIZON_HOURS,
) -> WeatherResult:
    """Hourly precipitation per site with the ladder: live -> cache -> replay."""
    if not sites:
        return WeatherResult(mode=mode, source=mode, degraded=False, sites={})

    if mode == SYNTHETIC:
        series = _fill_missing_zeros(_load_file_series("synthetic_storm", sites), sites)
        return _result(mode, SYNTHETIC, False, sites, series, horizon_hours)

    if mode == REPLAY:
        series = _fill_missing_zeros(_load_file_series("replay_michaung", sites), sites)
        return _result(mode, REPLAY, False, sites, series, horizon_hours)

    if mode != LIVE:
        raise ValueError(f"unknown weather mode {mode!r}; expected live|replay|synthetic")

    # --- live with the degradation ladder ---
    try:
        fetched = _fetch_live(sites)
        _store_cache(session, sites, fetched)
        return _result(LIVE, LIVE, False, sites, fetched, horizon_hours)
    except Exception as error:  # noqa: BLE001 - any live failure degrades, never crashes
        logger.warning("live forecast failed (%s: %s); falling back", type(error).__name__, error)

    cached = _read_cached(session, sites)
    if len(cached) == len(sites):
        return _result(LIVE, CACHE, True, sites, cached, horizon_hours)
    if cached:
        # partial cache: fill the rest from replay, still flagged degraded
        replay = _load_file_series("replay_michaung", sites)
        merged = {**replay, **cached}
        return _result(LIVE, CACHE, True, sites, _fill_missing_zeros(merged, sites), horizon_hours)

    replay = _fill_missing_zeros(_load_file_series("replay_michaung", sites), sites)
    return _result(LIVE, REPLAY, True, sites, replay, horizon_hours)


def _result(
    mode: str,
    source: str,
    degraded: bool,
    sites: list[SiteSpec],
    series: dict[str, tuple[float, ...]],
    horizon_hours: int,
) -> WeatherResult:
    return WeatherResult(
        mode=mode,
        source=source,
        degraded=degraded,
        sites={
            site.site_id: SiteSeries(
                site_id=site.site_id,
                lat=site.lat,
                lon=site.lon,
                series=tuple(series[site.site_id][:horizon_hours]),
                source=source,
                degraded=degraded,
            )
            for site in sites
        },
    )


def clear_forecast_cache(session: Session) -> None:
    """Test helper: empty the stored forecast cache."""
    from sqlalchemy import delete

    session.execute(delete(ForecastCache))
    session.commit()


def fetched_at_label(result: WeatherResult, reference: datetime | None = None) -> str:
    stamp = reference or now()
    return stamp.strftime("%Y-%m-%d %H:%M UTC")