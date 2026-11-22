"""Dashboard auto-run orchestration (section 8.1).

GET /dashboard/{id} does, in order:
  1. exposure for the owner + its vendors + every partner (TTL-cached weather);
  2. if an alert is active -> run or reuse the AUTO stress test
     (idempotent on (factory_id, forecast_hash));
  3. top 3 SPOFs;
  4. readiness for 24/48/72 with the headline at the default window;
  5. stale-partner count.
One payload, honestly labelled SIMULATED SAMPLE.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.enums import Role
from app.errors import AppError
from app.models import ExposureSnapshot, Factory
from app.services import exposure as exposure_service
from app.services import readiness as readiness_service
from app.services import spof as spof_service
from app.services import stress as stress_service

DATA_LABEL = "SIMULATED SAMPLE"


def _factory(session: Session, factory_id: str) -> Factory:
    factory = session.get(Factory, factory_id)
    if factory is None:
        raise AppError("NOT_FOUND", f"Factory {factory_id!r} does not exist.", status_code=404)
    if factory.role != Role.OWNER:
        raise AppError(
            "NOT_AN_OWNER",
            f"The dashboard is for an owner factory; {factory_id!r} is a partner.",
            status_code=409,
        )
    return factory


def dashboard_out(session: Session, factory_id: str) -> dict:
    factory = _factory(session, factory_id)

    # 1. exposure (owner + vendors + partners; snapshot written by compute_exposure)
    exposure_result = exposure_service.compute_exposure(session, factory.id)
    owner = exposure_result.sites[factory.id]
    snapshot_id = f"exp_{exposure_result.forecast_hash[:16]}_{factory.id}"
    snapshot = session.get(ExposureSnapshot, snapshot_id)

    # 2. auto stress test when the alert is active (idempotent)
    stress_id = None
    if exposure_result.alert.active and snapshot is not None:
        stress = stress_service.run_auto_for_alert(session, snapshot)
        if stress is not None:
            stress_id = stress.id

    # 3. top 3 SPOFs
    spof_result, _trace = spof_service.compute_spof(session, factory.id)
    spof_top = [
        {
            "rank": item.rank,
            "resource_id": item.resource_id,
            "kind": item.kind,
            "name": item.name,
            "orders_broken": list(item.orders_broken),
            "steps_broken": list(item.steps_broken),
            "revenue_at_risk_inr": item.revenue_at_risk_inr,
            "exposed": item.exposed,
        }
        for item in spof_result.items[:3]
    ]

    # 4. readiness for 24/48/72 (headline = default window)
    readiness = readiness_service.readiness_out(session, factory.id)
    windows = {str(w["window_hours"]): w["weighted_score"] for w in readiness["windows"]}
    headline = {
        "window": readiness["window_hours"],
        "score": readiness["score"],
        "weighted": readiness["weighted_score"],
    }

    # 5. stale partners (readiness already counted them)
    stale_partners = readiness["stale_partners"]

    alert_payload = {
        "active": exposure_result.alert.active,
        "headline": exposure_result.alert.headline,
        "onset_in_hours": exposure_result.alert.onset_in_hours,
        "stress_test_id": stress_id,
        "cta": "START_RECOVERY" if stress_id is not None else None,
    }

    exposure_summary = {
        "owner_site_risk": owner.site_risk,
        "owner_risk_level": owner.risk_level.value,
        "owner_max24_mm": owner.max24_mm,
        "owner_onset_in_hours": owner.onset_in_hours,
        "owner_wet_spell_hours": owner.wet_spell_hours,
        "isolation": exposure_result.isolation,
        "routes": [
            {"route_id": r.route_id, "exit_id": r.exit_id, "route_risk": r.route_risk, "exposed": r.exposed}
            for r in exposure_result.owner_routes
        ],
        "site_risks": {
            site_id: item.site_risk
            for site_id, item in sorted(exposure_result.sites.items())
        },
    }

    return {
        "factory": {
            "id": factory.id,
            "name": factory.name,
            "role": factory.role.value,
            "cluster_id": factory.cluster_id,
            "hazard_zone_id": factory.hazard_zone_id,
            "grid_id": factory.grid_id,
        },
        "data_label": DATA_LABEL,
        "weather": {
            "mode": exposure_result.mode,
            "source": exposure_result.source,
            "degraded": exposure_result.degraded,
            "attribution": exposure_result.attribution,
        },
        "readiness": {"headline": headline, "windows": windows},
        "alert": alert_payload,
        "spof_top": spof_top,
        "exposure_summary": exposure_summary,
        "stale_partners": stale_partners,
    }
