"""M4 routers: exposure per factory, exposure map, and the demo weather switch."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config_loader import load_configs
from app.db import get_db
from app.schemas.dashboard import DemoModeIn, DemoStateOut
from app.schemas.exposure import (
    AlertOut,
    ExposureMapOut,
    ExposureOut,
    MapPoint,
    RouteRiskOut,
    SiteRisk,
    WeatherInfo,
)
from app.services import exposure as service
from app.settings import get_settings

router = APIRouter(tags=["exposure"])

DATA_LABEL = "SIMULATED SAMPLE"


def _weather_info(result) -> WeatherInfo:
    return WeatherInfo(
        mode=result.mode,
        source=result.source,
        degraded=result.degraded,
        attribution=result.attribution,
    )


def _site_risk(item, isolation: bool) -> SiteRisk:
    return SiteRisk(
        site_id=item.site_id,
        site_role=item.site_role,
        site_risk=item.site_risk,
        risk_level=item.risk_level,
        max24_mm=item.max24_mm,
        peak3_mm=item.peak3_mm,
        hazard=item.hazard,
        vulnerability=item.vulnerability,
        onset_in_hours=float(item.onset_in_hours) if item.onset_in_hours is not None else None,
        wet_spell_hours=item.wet_spell_hours,
        isolation=isolation,
        drivers=list(item.drivers),
    )


@router.get(
    "/factories/{factory_id}/exposure",
    response_model=ExposureOut,
    summary="Compute site and route exposure",
)
def get_exposure(
    factory_id: str,
    mode: str | None = Query(default=None, pattern="^(live|replay|synthetic)$"),
    session: Session = Depends(get_db),
):
    result = service.compute_exposure(session, factory_id, mode)
    owner = result.sites[factory_id]
    alert = None
    if result.alert.active:
        alert = AlertOut(
            active=True,
            level=result.alert.level,
            onset_in_hours=result.alert.onset_in_hours,
            max_24h_mm=result.alert.max_24h_mm,
            affected_sites=list(result.alert.affected_sites),
            headline=result.alert.headline,
        )
    return ExposureOut(
        factory_id=factory_id,
        computed_at=result.computed_at,
        weather=_weather_info(result),
        site=_site_risk(owner, result.isolation),
        routes=[
            RouteRiskOut(
                route_id=route.route_id,
                exit_id=route.exit_id,
                route_risk=route.route_risk,
                low_share=route.low_share,
                underpass_count=route.underpass_count,
                exposed=route.exposed,
            )
            for route in result.owner_routes
        ],
        alert=alert,
        trace=result.trace,
    )


@router.get(
    "/exposure/map",
    response_model=ExposureMapOut,
    summary="Compute risk-ranked sites for the map",
)
def get_exposure_map(
    mode: str | None = Query(default=None, pattern="^(live|replay|synthetic)$"),
    session: Session = Depends(get_db),
):
    points, resolved_mode, source, degraded = service.compute_map(session, mode)
    return ExposureMapOut(
        mode=resolved_mode,
        weather=WeatherInfo(
            mode=resolved_mode,
            source=source,
            degraded=degraded,
            attribution="Weather data by Open-Meteo.com",
        ),
        points=[
            MapPoint(
                site_id=point.site_id,
                role=point.site_role,
                name=point.name,
                lat=point.lat,
                lon=point.lon,
                site_risk=point.site_risk,
                risk_level=point.risk_level,
                isolation=False,
            )
            for point in points
        ],
    )


@router.post(
    "/demo/mode",
    response_model=DemoStateOut,
    summary="Set the demo weather mode",
)
def post_demo_mode(payload: DemoModeIn, session: Session = Depends(get_db)):
    mode = service.set_mode(session, payload.weather)
    settings = get_settings()
    return DemoStateOut(
        weather_mode=mode,
        replay_event=settings.replay_event,
        data_label=DATA_LABEL,
    )


@router.get(
    "/demo/state",
    response_model=DemoStateOut,
    summary="Read current demo mode and sample label",
)
def get_demo_state(session: Session = Depends(get_db)):
    settings = get_settings()
    return DemoStateOut(
        weather_mode=service.resolve_mode(session, None),
        replay_event=load_configs().cluster.replay.event if load_configs().cluster.replay else settings.replay_event,
        data_label=DATA_LABEL,
    )
