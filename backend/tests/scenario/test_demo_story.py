"""Phase 14 end-to-end rehearsal of the replay-mode RELAY story."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.core import clock
from app.demo_seed import reset_demo
from app.services import exposure as exposure_service
from app.settings import get_settings

BACKEND_DIR = Path(__file__).resolve().parents[2]
FROZEN = datetime(2026, 11, 14, 9, 0, 0, tzinfo=timezone.utc)
TRACKING_STEPS = [
    "REQUEST_SENT",
    "PARTNER_RESPONSE",
    "TECHNICAL_AND_CUSTOMER_APPROVALS",
    "PRODUCTION_SCHEDULED",
    "PRODUCTION_STARTED",
    "QUALITY_INSPECTION",
    "DISPATCH_AND_DELIVERY",
]


@pytest.fixture()
def story_client(monkeypatch):
    """Use only committed cache/replay/manual paths; never let this suite use a key."""
    monkeypatch.setenv("WEATHER_MODE", "replay")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("GEMINI_MODEL", "")
    monkeypatch.setenv("VISION_PROVIDER_CHAIN", "cache,gemini")
    get_settings.cache_clear()
    from fastapi.testclient import TestClient

    from app.main import create_app

    try:
        with clock.frozen_time(FROZEN):
            reset_demo()
            exposure_service.reset_weather_ttl()
            with TestClient(create_app()) as test_client:
                yield test_client
    finally:
        get_settings.cache_clear()


def _complete_hosur(client):
    for key in ("CAPACITY_RECONFIRMED", "CUSTOMER_APPROVED"):
        response = client.post(f"/api/v1/relationships/rel_hosur/checks/{key}/complete")
        assert response.status_code == 200, response.text
    ready = client.patch("/api/v1/relationships/rel_hosur/status", json={"status": "READY"})
    assert ready.status_code == 200, ready.text


def test_full_replay_story_works_without_provider_keys(story_client):
    client = story_client

    # 1. Reset and dashboard auto-run in replay mode.
    state = client.get("/api/v1/demo/state")
    assert state.status_code == 200
    assert state.json()["weather_mode"] == "replay"
    dashboard_response = client.get("/api/v1/dashboard/fac_owner")
    assert dashboard_response.status_code == 200, dashboard_response.text
    dashboard = dashboard_response.json()
    assert dashboard["data_label"] == "SIMULATED SAMPLE"
    assert dashboard["weather"]["mode"] == "replay"
    assert dashboard["alert"]["active"] is True
    assert dashboard["alert"]["stress_test_id"]

    stress_response = client.get(f"/api/v1/stress-tests/{dashboard['alert']['stress_test_id']}")
    assert stress_response.status_code == 200, stress_response.text
    stress = stress_response.json()
    assert stress["summary"]["orders_at_risk"] >= 2
    assert stress["summary"]["revenue_exposed_inr"] >= 1_000_000
    assert stress["summary"]["orders_no_fallback"] >= 1

    # 2. The resource ranking agrees with the seeded dependency story.
    spof_response = client.get("/api/v1/factories/fac_owner/spof")
    assert spof_response.status_code == 200, spof_response.text
    spofs = spof_response.json()["items"]
    by_resource = {item["resource_id"]: item for item in spofs}
    assert spofs[0]["resource_id"] in {"ven_heat", "mch_own_grind_1"}
    assert by_resource["ven_heat"]["exposed"] is True
    assert by_resource["mch_own_grind_1"]["exposed"] is True

    # 3. Golden-cache drawing → passport → redacted RFQ (no Gemini key needed).
    drawing = (BACKEND_DIR / "data" / "drawings" / "pump_shaft.png").read_bytes()
    extracted = client.post(
        "/api/v1/passports/extract",
        files={"file": ("pump_shaft.png", drawing, "image/png")},
    )
    assert extracted.status_code == 200, extracted.text
    passport_id = extracted.json()["passport_id"]
    assert extracted.json()["extraction_meta"]["provider"] == "cache"
    reviewed = client.patch(
        f"/api/v1/passports/{passport_id}",
        json={
            "data": {
                "quantity": 200,
                "material": {"grade": "EN8", "standard": None, "form": None},
                "process_route": [{"process": "TURN"}, {"process": "MILL"}],
                "tightest_tolerance_mm": 0.02,
            }
        },
    )
    assert reviewed.status_code == 200, reviewed.text
    confirmed = client.post(f"/api/v1/passports/{passport_id}/confirm")
    assert confirmed.status_code == 200, confirmed.text
    rfq = client.get(f"/api/v1/passports/{passport_id}/rfq")
    assert rfq.status_code == 200, rfq.text
    flat_rfq = json.dumps(rfq.json()) + rfq.json()["text"]
    for private_value in ("DWG-PSH-014", "Pump shaft", "ACME"):
        assert private_value not in flat_rfq

    # 4. Matching for the hero order returns the Ready, Pending and excluded story.
    matching = client.post("/api/v1/matching/search", json={"order_id": "ord_102"})
    assert matching.status_code == 200, matching.text
    candidates = matching.json()["candidates"]
    viable = [candidate for candidate in candidates if not candidate["excluded"]]
    assert [candidate["partner_id"] for candidate in viable if candidate["effective_status"] == "READY"] == ["fac_oragadam"]
    assert [candidate["partner_id"] for candidate in viable if candidate["effective_status"] == "APPROVAL_PENDING"] == ["fac_hosur"]
    assert any(candidate["excluded"] and candidate["exclusion_reason"] == "ALSO_EXPOSED_SAME_EVENT" for candidate in candidates)

    # 5. Prefilled recovery, Ready selection, redacted handover and fixed stepper.
    recovery = client.post(
        "/api/v1/recovery-requests",
        json={"from_stress_test_id": dashboard["alert"]["stress_test_id"], "order_id": "ord_102"},
    )
    assert recovery.status_code == 201, recovery.text
    recovery_id = recovery.json()["id"]
    options = {item["partner_id"]: item for item in recovery.json()["options"]}
    assert options["fac_oragadam"]["status"] == "READY"
    assert options["fac_hosur"]["status"] == "APPROVAL_PENDING"
    assert options["fac_amb_nb"]["excluded"] is True
    assert options["fac_guindy"]["exclusion_reason"] == "ALSO_EXPOSED_SAME_EVENT"

    selected = client.post(
        f"/api/v1/recovery-requests/{recovery_id}/select-partner",
        json={"partner_id": "fac_oragadam"},
    )
    assert selected.status_code == 200, selected.text
    handover = client.get(f"/api/v1/recovery-requests/{recovery_id}/handover")
    assert handover.status_code == 200, handover.text
    assert handover.json()["data_label"] == "SIMULATED SAMPLE"
    assert "human, customer and contractual approvals" in handover.json()["text"]

    for expected_step in TRACKING_STEPS[1:]:
        advanced = client.post(f"/api/v1/recovery-requests/{recovery_id}/tracking/advance")
        assert advanced.status_code == 200, advanced.text
        states = {step["step_key"]: step["state"] for step in advanced.json()["steps"]}
        assert states[expected_step] == "DONE"

    # 6. Peenya is stale and does not count; Hosur checks close a real readiness gap.
    before = client.get("/api/v1/readiness/fac_owner")
    assert before.status_code == 200
    before_score = before.json()["weighted_score"]
    assert 30 <= before_score <= 55
    review = {item["partner_id"]: item for item in before.json()["review"]}
    assert review["fac_peenya"]["effective_status"] == "STALE"
    assert all(item["covered_by"] != "fac_peenya" for item in before.json()["breakdown"])

    _complete_hosur(client)
    after = client.get("/api/v1/readiness/fac_owner")
    assert after.status_code == 200
    assert after.json()["weighted_score"] - before_score >= 10

    # 7. No external credential was required by the full run.
    health = client.get("/api/v1/health").json()
    gemini = next(provider for provider in health["vision_chain"] if provider["provider"] == "gemini")
    assert gemini["configured"] is False
