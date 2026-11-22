"""Phase 14 warm/cold endpoint and cached-drawing performance budgets."""

from __future__ import annotations

import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]


def test_warm_cold_dashboard_stress_matching_and_cached_passport_budgets(phase14_client):
    client = phase14_client
    cold_started = time.perf_counter()
    dashboard = client.get("/api/v1/dashboard/fac_owner")
    cold_s = time.perf_counter() - cold_started
    assert dashboard.status_code == 200, dashboard.text
    assert cold_s < 6.0, f"cold dashboard took {cold_s:.3f}s"

    warm_started = time.perf_counter()
    warm = client.get("/api/v1/dashboard/fac_owner")
    warm_s = time.perf_counter() - warm_started
    assert warm.status_code == 200, warm.text
    assert warm_s < 1.5, f"warm dashboard took {warm_s:.3f}s"

    stress_started = time.perf_counter()
    stress = client.post(
        "/api/v1/stress-tests",
        json={
            "factory_id": "fac_owner",
            "hazard": "FLOOD",
            "scope": {"type": "sites", "ids": ["fac_owner"]},
            "start_in_hours": 24,
            "duration_hours": 72,
        },
    )
    stress_s = time.perf_counter() - stress_started
    assert stress.status_code == 201, stress.text
    assert stress_s < 2.0, f"stress-test read took {stress_s:.3f}s"

    matching_started = time.perf_counter()
    matching = client.post("/api/v1/matching/search", json={"order_id": "ord_102"})
    matching_s = time.perf_counter() - matching_started
    assert matching.status_code == 200, matching.text
    assert matching_s < 1.0, f"matching took {matching_s:.3f}s"

    drawing = (BACKEND_DIR / "data" / "drawings" / "pump_shaft.png").read_bytes()
    passport_started = time.perf_counter()
    passport = client.post(
        "/api/v1/passports/extract",
        files={"file": ("pump_shaft.png", drawing, "image/png")},
    )
    passport_s = time.perf_counter() - passport_started
    assert passport.status_code == 200, passport.text
    assert passport.json()["extraction_meta"]["provider"] == "cache"
    assert passport_s < 3.0, f"cached passport extraction took {passport_s:.3f}s"
