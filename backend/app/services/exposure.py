"""M4 service: build exposure for a factory and for the map (section 7.2).

TTL cache: `cache_ttl_minutes` (exposure.yaml) caches the *weather fetch* per
(mode, site set) inside a process, because that is the expensive, network-bound
part. Exposure arithmetic is cheap and always recomputed from the series, so a
demo reset or a data change is never masked by a stale computed result.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app.adapters import weather
from app.config_loader import load_configs
from app.core import exposure_score
from app.core.clock import now
from app.core.locks import DEMO_WRITE_LOCK
from app.core.trace import TraceBuilder
from app.enums import RiskLevel
from app.errors import AppError
from app.models import AppState, ExposureSnapshot, Factory, Route, SiteTerrain, Vendor, VendorLink
from app.settings import get_settings

_WEATHER_MODE_KEY = "weather_mode"
_TTL_CACHE: dict[tuple[str, tuple[str, ...]], tuple[object, weather.WeatherResult]] = {}


def reset_weather_ttl() -> None:
    """Clear the in-process weather TTL cache (tests, demo reset)."""
    _TTL_CACHE.clear()


@dataclass(frozen=True)
class SiteFacts:
    site_id: str
    name: str
    role: str  # OWNER | PARTNER | VENDOR | SUPPLIER
    lat: float
    lon: float
    cluster_id: str
    grid_id: str | None
    hazard_zone_id: str | None
    elevation_m: float | None = None
    ring_mean_m: float | None = None
    nearest_water_m: float | None = None
    zone_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RouteRisk:
    route_id: str
    exit_id: str
    route_risk: int | None
    low_share: float | None
    underpass_count: int | None
    exposed: bool


@dataclass(frozen=True)
class AlertDecision:
    active: bool
    level: RiskLevel | None = None
    onset_in_hours: float | None = None
    max_24h_mm: float | None = None
    affected_sites: tuple[str, ...] = ()
    headline: str | None = None


@dataclass(frozen=True)
class ExposureResult:
    factory_id: str
    mode: str
    source: str
    degraded: bool
    attribution: str
    sites: dict[str, exposure_score.SiteExposure]
    owner_routes: tuple[RouteRisk, ...]
    isolation: bool
    alert: AlertDecision
    forecast_hash: str
    computed_at: object
    trace: list[dict]


def resolve_mode(session: Session, mode: str | None) -> str:
    """Explicit ?mode= wins, then the demo app_state, then the .env default."""
    if mode:
        normalized = mode.strip().lower()
        if normalized not in {"live", "replay", "synthetic"}:
            raise AppError(
                "VALIDATION_ERROR",
                f"Unknown weather mode {mode!r}.",
                status_code=422,
                details={"allowed": ["live", "replay", "synthetic"]},
            )
        return normalized
    row = session.get(AppState, _WEATHER_MODE_KEY)
    if row and isinstance(row.value, dict) and row.value.get("mode") in {"live", "replay", "synthetic"}:
        return str(row.value["mode"])
    return get_settings().weather_mode


def set_mode(session: Session, mode: str) -> str:
    normalized = mode.strip().lower()
    if normalized not in {"live", "replay", "synthetic"}:
        raise AppError(
            "VALIDATION_ERROR",
            f"Unknown weather mode {mode!r}.",
            status_code=422,
            details={"allowed": ["live", "replay", "synthetic"]},
        )
    row = session.get(AppState, _WEATHER_MODE_KEY)
    if row is None:
        session.add(AppState(key=_WEATHER_MODE_KEY, value={"mode": normalized}))
    else:
        row.value = {"mode": normalized}
    session.commit()
    reset_weather_ttl()
    return normalized


def _site_rows(session: Session, factory_id: str) -> list[SiteFacts]:
    """Owner + its approved vendors/suppliers + every partner (partners feed the map and M6)."""
    factory = session.get(Factory, factory_id)
    if factory is None:
        raise AppError("NOT_FOUND", f"Factory {factory_id!r} does not exist.", status_code=404)

    facts: list[SiteFacts] = [
        SiteFacts(
            site_id=factory.id,
            name=factory.name,
            role=factory.role.value,
            lat=factory.lat,
            lon=factory.lon,
            cluster_id=factory.cluster_id,
            grid_id=factory.grid_id,
            hazard_zone_id=factory.hazard_zone_id,
        )
    ]

    for link in session.scalars(select(VendorLink).where(VendorLink.factory_id == factory_id)):
        vendor = session.get(Vendor, link.vendor_id)
        if vendor is None:
            continue
        facts.append(
            SiteFacts(
                site_id=vendor.id,
                name=vendor.name,
                role=vendor.kind.value,
                lat=vendor.lat,
                lon=vendor.lon,
                cluster_id=vendor.cluster_id,
                grid_id=vendor.grid_id,
                hazard_zone_id=vendor.hazard_zone_id,
            )
        )

    for partner in session.scalars(select(Factory).where(Factory.role == "PARTNER").order_by(Factory.id)):
        if partner.id == factory_id:
            continue
        facts.append(
            SiteFacts(
                site_id=partner.id,
                name=partner.name,
                role=partner.role.value,
                lat=partner.lat,
                lon=partner.lon,
                cluster_id=partner.cluster_id,
                grid_id=partner.grid_id,
                hazard_zone_id=partner.hazard_zone_id,
            )
        )

    # attach prefetched terrain facts (Phase 4); missing rows degrade honestly
    terrain = {
        row.site_id: row
        for row in session.scalars(
            select(SiteTerrain).where(SiteTerrain.site_id.in_([f.site_id for f in facts]))
        )
    }
    enriched: list[SiteFacts] = []
    for site in facts:
        row = terrain.get(site.site_id)
        if row is None:
            enriched.append(site)
        else:
            enriched.append(
                SiteFacts(
                    site_id=site.site_id,
                    name=site.name,
                    role=site.role,
                    lat=site.lat,
                    lon=site.lon,
                    cluster_id=site.cluster_id,
                    grid_id=site.grid_id,
                    hazard_zone_id=site.hazard_zone_id,
                    elevation_m=row.elevation_m,
                    ring_mean_m=row.ring_mean_m,
                    nearest_water_m=row.nearest_water_m,
                    zone_ids=list(row.zone_ids or []),
                )
            )
    return enriched


def _weather_for(session: Session, sites: list[SiteFacts], mode: str, ttl_minutes: int) -> weather.WeatherResult:
    key = (mode, tuple(sorted(site.site_id for site in sites)))
    cached = _TTL_CACHE.get(key)
    if cached is not None:
        stamp, result = cached
        if now() - stamp < timedelta(minutes=ttl_minutes):  # type: ignore[operator]
            return result
    result = weather.get_hourly_precip(
        session,
        [weather.SiteSpec(site_id=site.site_id, lat=site.lat, lon=site.lon) for site in sites],
        mode,
    )
    _TTL_CACHE[key] = (now(), result)
    return result


def forecast_hash_for(series_by_site: dict[str, tuple[float, ...]]) -> str:
    """Stable hash of the forecast, used for auto-run idempotency (section 3.5)."""
    digest = hashlib.sha256()
    for site_id in sorted(series_by_site):
        digest.update(site_id.encode("utf-8"))
        digest.update(json.dumps([round(v, 3) for v in series_by_site[site_id]]).encode("utf-8"))
    return digest.hexdigest()[:32]


def _risk_level(score: int) -> RiskLevel:
    return RiskLevel.from_score(score)


def _owner_routes(session: Session, site_id: str, hazard: float, cfg) -> tuple[RouteRisk, ...]:
    rows = session.scalars(select(Route).where(Route.site_id == site_id).order_by(Route.id)).all()
    out: list[RouteRisk] = []
    for row in rows:
        facts = exposure_score.RouteFacts(
            route_id=row.id, exit_id=row.exit_id, low_share=row.low_share, underpass_count=row.underpass_count
        )
        risk = exposure_score.route_risk(hazard, facts, cfg)
        out.append(
            RouteRisk(
                route_id=row.id,
                exit_id=row.exit_id,
                route_risk=risk,
                low_share=row.low_share,
                underpass_count=row.underpass_count,
                exposed=bool(risk is not None and risk >= cfg.alert_threshold),
            )
        )
    return tuple(out)


def compute_exposure(session: Session, factory_id: str, mode: str | None = None) -> ExposureResult:
    bundle = load_configs()
    cfg = bundle.exposure
    resolved_mode = resolve_mode(session, mode)

    sites = _site_rows(session, factory_id)
    weather_result = _weather_for(session, sites, resolved_mode, cfg.cache_ttl_minutes)

    trace = TraceBuilder()
    trace.add(
        "weather",
        f"Hourly precipitation for {len(sites)} sites ({resolved_mode} mode, source={weather_result.source}).",
        inputs={"mode": resolved_mode},
        output={
            "source": weather_result.source,
            "degraded": weather_result.degraded,
            "attribution": weather_result.attribution,
            "sites": len(sites),
        },
    )

    exposures: dict[str, exposure_score.SiteExposure] = {}
    for site in sites:
        series = list(weather_result.series(site.site_id))
        rain = exposure_score.rain_hazard(series, cfg)
        vuln = exposure_score.vulnerability(
            elevation_m=site.elevation_m if site.elevation_m is not None else (site.ring_mean_m or 0.0),
            ring_mean_m=site.ring_mean_m if site.ring_mean_m is not None else (site.elevation_m or 0.0),
            nearest_water_m=site.nearest_water_m,
            zone_ids=list(site.zone_ids) or ([site.hazard_zone_id] if site.hazard_zone_id else []),
            cfg=cfg,
        )
        risk = exposure_score.site_risk(rain.hazard, vuln, cfg)
        onset, spell = exposure_score.onset_and_wet_spell(series, cfg)
        drivers = exposure_score.explain_drivers(rain=rain, vuln=vuln, role=site.role, cfg=cfg)
        exposures[site.site_id] = exposure_score.SiteExposure(
            site_id=site.site_id,
            site_role=site.role,
            site_risk=risk,
            risk_level=_risk_level(risk),
            max24_mm=rain.max24_mm,
            peak3_mm=rain.peak3_mm,
            hazard=rain.hazard,
            vulnerability=vuln.value,
            onset_in_hours=onset,
            wet_spell_hours=spell,
            drivers=tuple(drivers),
            name=site.name,
            lat=site.lat,
            lon=site.lon,
        )
        trace.add(
            "site_risk",
            f"{site.name}: {rain.max24_mm:.0f} mm/24 h -> hazard {rain.hazard:.2f}; "
            f"vulnerability {vuln.value:.2f} -> risk {risk} ({_risk_level(risk).value}).",
            inputs={
                "site_id": site.site_id,
                "max24_mm": rain.max24_mm,
                "peak3_mm": rain.peak3_mm,
                "depression": vuln.depression,
                "water_proximity": vuln.water_proximity,
                "flood_history": vuln.flood_history,
            },
            output={"site_risk": risk, "risk_level": _risk_level(risk).value},
        )

    owner = exposures[factory_id]
    owner_routes = _owner_routes(session, factory_id, owner.hazard, cfg)
    isolation = exposure_score.is_isolated([route.route_risk for route in owner_routes], cfg)
    if owner_routes:
        trace.add(
            "routes",
            f"{len(owner_routes)} access route(s) scored from low-elevation share and underpasses.",
            output={
                "routes": [
                    {"route_id": r.route_id, "exit_id": r.exit_id, "route_risk": r.route_risk, "exposed": r.exposed}
                    for r in owner_routes
                ],
                "isolation": isolation,
            },
        )

    alert = _build_alert(session, factory_id, exposures, cfg, trace)
    forecast_hash = forecast_hash_for({site.site_id: weather_result.series(site.site_id) for site in sites})
    computed_at = now()

    snapshot = ExposureSnapshot(
        id=f"exp_{forecast_hash[:16]}_{factory_id}",
        factory_id=factory_id,
        mode=resolved_mode,
        computed_at=computed_at,
        forecast_hash=forecast_hash,
        result={
            "sites": {site_id: _exposure_payload(item) for site_id, item in exposures.items()},
            "alert": _alert_payload(alert),
            "weather": {"mode": resolved_mode, "source": weather_result.source, "degraded": weather_result.degraded},
            "isolation": isolation,
            "routes": [
                {"route_id": r.route_id, "exit_id": r.exit_id, "route_risk": r.route_risk, "exposed": r.exposed}
                for r in owner_routes
            ],
        },
        alert=alert.active,
    )
    # End any earlier read transaction so this check-then-write sees the latest
    # committed world (a concurrent demo reset may have just replaced the rows).
    session.rollback()
    with DEMO_WRITE_LOCK:
        existing = session.get(ExposureSnapshot, snapshot.id)
        if existing is None:
            session.add(snapshot)
            try:
                session.commit()
            except IntegrityError:
                # Concurrent dashboard requests can compute the same deterministic
                # snapshot. Keep the winner and continue with the same calculation.
                session.rollback()
                if session.get(ExposureSnapshot, snapshot.id) is None:
                    raise
        else:
            try:
                existing.result = snapshot.result
                existing.alert = snapshot.alert
                existing.computed_at = computed_at
                session.commit()
            except StaleDataError:
                # The row was replaced by a demo reset between the read and the
                # write. Re-read and store the freshly computed snapshot.
                session.rollback()
                session.merge(snapshot)
                session.commit()

    return ExposureResult(
        factory_id=factory_id,
        mode=resolved_mode,
        source=weather_result.source,
        degraded=weather_result.degraded,
        attribution=weather_result.attribution,
        sites=exposures,
        owner_routes=owner_routes,
        isolation=isolation,
        alert=alert,
        forecast_hash=forecast_hash,
        computed_at=computed_at,
        trace=trace.to_list(),
    )


def _build_alert(
    session: Session,
    factory_id: str,
    exposures: dict[str, exposure_score.SiteExposure],
    cfg,
    trace: TraceBuilder,
) -> AlertDecision:
    """Alert when the owner or one of its approved vendors is at/above the threshold."""
    key_vendors = [link.vendor_id for link in session.scalars(select(VendorLink).where(VendorLink.factory_id == factory_id))]
    watched = [factory_id, *key_vendors]
    affected = exposure_score.alert_affected(watched, exposures, cfg.alert_threshold)
    if not affected:
        trace.add(
            "alert",
            f"No site at or above the alert threshold ({cfg.alert_threshold}).",
            output={"active": False},
        )
        return AlertDecision(active=False)

    peak = max(affected, key=lambda site_id: exposures[site_id].site_risk)
    peak_exposure = exposures[peak]
    onset = min(
        (exposures[site_id].onset_in_hours for site_id in affected if exposures[site_id].onset_in_hours is not None),
        default=None,
    )
    level = peak_exposure.risk_level
    headline = (
        f"Heavy rain in {onset} h: {len(affected)} site(s) in the storm footprint at "
        f"{peak_exposure.site_risk}/100 ({level.value}) - risk indicator, not a flood model"
        if onset is not None
        else f"{len(affected)} site(s) at {peak_exposure.site_risk}/100 ({level.value})"
    )
    trace.add(
        "alert",
        f"Alert raised: {', '.join(affected)} at or above {cfg.alert_threshold}; peak {peak} = "
        f"{peak_exposure.site_risk} ({level.value}).",
        output={"active": True, "level": level.value, "affected_sites": affected, "onset_in_hours": onset},
    )
    return AlertDecision(
        active=True,
        level=level,
        onset_in_hours=float(onset) if onset is not None else None,
        max_24h_mm=peak_exposure.max24_mm,
        affected_sites=tuple(affected),
        headline=headline,
    )


def _exposure_payload(item: exposure_score.SiteExposure) -> dict:
    return {
        "site_id": item.site_id,
        "site_role": item.site_role,
        "site_risk": item.site_risk,
        "risk_level": item.risk_level.value,
        "max24_mm": item.max24_mm,
        "peak3_mm": item.peak3_mm,
        "hazard": item.hazard,
        "vulnerability": item.vulnerability,
        "onset_in_hours": item.onset_in_hours,
        "wet_spell_hours": item.wet_spell_hours,
        "drivers": list(item.drivers),
    }


def _alert_payload(alert: AlertDecision) -> dict:
    return {
        "active": alert.active,
        "level": alert.level.value if alert.level else None,
        "onset_in_hours": alert.onset_in_hours,
        "max_24h_mm": alert.max_24h_mm,
        "affected_sites": list(alert.affected_sites),
        "headline": alert.headline,
    }


def compute_map(session: Session, mode: str | None = None) -> tuple[list[exposure_score.SiteExposure], str, str, bool]:
    """Every demo site with its risk for the map (section 8 GET /exposure/map)."""
    bundle = load_configs()
    cfg = bundle.exposure
    resolved_mode = resolve_mode(session, mode)

    sites: list[SiteFacts] = []
    for factory in session.scalars(select(Factory).order_by(Factory.id)):
        sites.append(
            SiteFacts(
                site_id=factory.id,
                name=factory.name,
                role=factory.role.value,
                lat=factory.lat,
                lon=factory.lon,
                cluster_id=factory.cluster_id,
                grid_id=factory.grid_id,
                hazard_zone_id=factory.hazard_zone_id,
            )
        )
    for vendor in session.scalars(select(Vendor).order_by(Vendor.id)):
        sites.append(
            SiteFacts(
                site_id=vendor.id,
                name=vendor.name,
                role=vendor.kind.value,
                lat=vendor.lat,
                lon=vendor.lon,
                cluster_id=vendor.cluster_id,
                grid_id=vendor.grid_id,
                hazard_zone_id=vendor.hazard_zone_id,
            )
        )

    terrain = {row.site_id: row for row in session.scalars(select(SiteTerrain))}
    for index, site in enumerate(sites):
        row = terrain.get(site.site_id)
        if row is not None:
            sites[index] = SiteFacts(
                site_id=site.site_id,
                name=site.name,
                role=site.role,
                lat=site.lat,
                lon=site.lon,
                cluster_id=site.cluster_id,
                grid_id=site.grid_id,
                hazard_zone_id=site.hazard_zone_id,
                elevation_m=row.elevation_m,
                ring_mean_m=row.ring_mean_m,
                nearest_water_m=row.nearest_water_m,
                zone_ids=list(row.zone_ids or []),
            )

    weather_result = _weather_for(session, sites, resolved_mode, cfg.cache_ttl_minutes)
    out: list[exposure_score.SiteExposure] = []
    for site in sites:
        series = list(weather_result.series(site.site_id))
        rain = exposure_score.rain_hazard(series, cfg)
        vuln = exposure_score.vulnerability(
            elevation_m=site.elevation_m if site.elevation_m is not None else (site.ring_mean_m or 0.0),
            ring_mean_m=site.ring_mean_m if site.ring_mean_m is not None else (site.elevation_m or 0.0),
            nearest_water_m=site.nearest_water_m,
            zone_ids=list(site.zone_ids) or ([site.hazard_zone_id] if site.hazard_zone_id else []),
            cfg=cfg,
        )
        onset, spell = exposure_score.onset_and_wet_spell(series, cfg)
        risk = exposure_score.site_risk(rain.hazard, vuln, cfg)
        out.append(
            exposure_score.SiteExposure(
                site_id=site.site_id,
                site_role=site.role,
                site_risk=risk,
                risk_level=_risk_level(risk),
                max24_mm=rain.max24_mm,
                peak3_mm=rain.peak3_mm,
                hazard=rain.hazard,
                vulnerability=vuln.value,
                onset_in_hours=onset,
                wet_spell_hours=spell,
                drivers=tuple(exposure_score.explain_drivers(rain=rain, vuln=vuln, role=site.role, cfg=cfg)),
                name=site.name,
                lat=site.lat,
                lon=site.lon,
            )
        )
    return out, resolved_mode, weather_result.source, weather_result.degraded
