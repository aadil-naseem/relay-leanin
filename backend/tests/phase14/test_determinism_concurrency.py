"""Dashboard reset determinism and concurrent auto-stress idempotency."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import engine
from app.enums import Trigger
from app.models import StressTest


def _stable_dashboard(payload: dict) -> dict:
    """Drop generated timestamps/ids while retaining every demo-story value."""
    return {
        "factory": payload["factory"],
        "data_label": payload["data_label"],
        "weather": payload["weather"],
        "readiness": payload["readiness"],
        "alert": {
            key: payload["alert"][key]
            for key in ("active", "headline", "onset_in_hours", "cta")
        },
        "spof_top": [
            {
                key: item[key]
                for key in (
                    "rank",
                    "kind",
                    "name",
                    "orders_broken",
                    "steps_broken",
                    "revenue_at_risk_inr",
                    "exposed",
                )
            }
            for item in payload["spof_top"]
        ],
        "exposure_summary": payload["exposure_summary"],
        "stale_partners": payload["stale_partners"],
    }


def _auto_stress_count() -> int:
    with Session(engine) as session:
        return int(
            session.scalar(
                select(func.count())
                .select_from(StressTest)
                .where(StressTest.factory_id == "fac_owner", StressTest.trigger == Trigger.AUTO)
            )
            or 0
        )


def test_reset_five_times_reproduces_the_same_dashboard(phase14_client):
    client = phase14_client
    dashboards = []
    for _ in range(5):
        reset = client.post("/api/v1/demo/reset")
        assert reset.status_code == 200, reset.text
        response = client.get("/api/v1/dashboard/fac_owner")
        assert response.status_code == 200, response.text
        dashboards.append(_stable_dashboard(response.json()))

    assert all(payload == dashboards[0] for payload in dashboards[1:])


def test_ten_parallel_dashboard_requests_create_one_auto_stress_row(phase14_client):
    # Start from a clean schema, then race the first cold auto-dashboard calls.
    reset = phase14_client.post("/api/v1/demo/reset")
    assert reset.status_code == 200

    with ThreadPoolExecutor(max_workers=10) as executor:
        responses = list(executor.map(
            lambda _index: phase14_client.get("/api/v1/dashboard/fac_owner"),
            range(10),
        ))

    assert [response.status_code for response in responses] == [200] * 10
    ids = {response.json()["alert"]["stress_test_id"] for response in responses}
    assert len(ids) == 1
    assert _auto_stress_count() == 1
