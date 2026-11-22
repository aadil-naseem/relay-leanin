"""OpenAPI contract snapshot and endpoint coverage for Phase 14."""

from __future__ import annotations

import json
from pathlib import Path

from app.main import create_app

REPO_DIR = Path(__file__).resolve().parents[3]
SNAPSHOT = REPO_DIR / "docs" / "openapi.snapshot.json"

REQUIRED_PATHS = {
    "/api/v1/health",
    "/api/v1/factories",
    "/api/v1/factories/{factory_id}",
    "/api/v1/factories/{factory_id}/machines",
    "/api/v1/machines/{machine_id}",
    "/api/v1/factories/{factory_id}/parts",
    "/api/v1/factories/{factory_id}/orders",
    "/api/v1/factories/{factory_id}/relationships",
    "/api/v1/relationships/{relationship_id}",
    "/api/v1/relationships/{relationship_id}/status",
    "/api/v1/relationships/{relationship_id}/checks/{key}/complete",
    "/api/v1/relationships/{relationship_id}/reconfirm",
    "/api/v1/factories/{factory_id}/spof",
    "/api/v1/factories/{factory_id}/exposure",
    "/api/v1/exposure/map",
    "/api/v1/stress-tests",
    "/api/v1/stress-tests/{test_id}",
    "/api/v1/matching/search",
    "/api/v1/readiness/{factory_id}",
    "/api/v1/readiness/{factory_id}/actions",
    "/api/v1/readiness/{factory_id}/history",
    "/api/v1/passports/extract",
    "/api/v1/passports/manual",
    "/api/v1/passports/{passport_id}",
    "/api/v1/passports/{passport_id}/confirm",
    "/api/v1/passports/{passport_id}/rfq",
    "/api/v1/passports/{passport_id}/share",
    "/api/v1/recovery-requests",
    "/api/v1/recovery-requests/{request_id}",
    "/api/v1/recovery-requests/{request_id}/select-partner",
    "/api/v1/recovery-requests/{request_id}/handover",
    "/api/v1/recovery-requests/{request_id}/tracking",
    "/api/v1/recovery-requests/{request_id}/tracking/advance",
    "/api/v1/dashboard/{factory_id}",
    "/api/v1/demo/reset",
    "/api/v1/demo/mode",
    "/api/v1/demo/state",
}


def _contract():
    return create_app().openapi()


def test_every_blueprint_endpoint_is_present_and_has_a_success_response():
    spec = _contract()
    paths = spec["paths"]
    assert REQUIRED_PATHS <= paths.keys()

    for path, operations in paths.items():
        if not path.startswith("/api/v1/"):
            continue
        for method, operation in operations.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            success = [
                (status, response)
                for status, response in operation["responses"].items()
                if status.startswith("2")
            ]
            assert success, f"{method.upper()} {path} has no documented success response"
            for status, response in success:
                if status == "204":
                    assert "content" not in response, f"{method.upper()} {path} must be bodyless"
                    continue
                assert "application/json" in response.get("content", {}), f"{method.upper()} {path}"
                assert "schema" in response["content"]["application/json"], f"{method.upper()} {path}"


def test_openapi_snapshot_matches_runtime_contract():
    assert SNAPSHOT.is_file(), f"Run backend/scripts/export_openapi.py to create {SNAPSHOT}"
    expected = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    assert _contract() == expected


def test_main_request_payloads_have_examples_and_descriptive_summaries():
    spec = _contract()
    schemas = spec["components"]["schemas"]
    for name in (
        "StressCreate",
        "MatchRequest",
        "RecoveryCreate",
        "DemoModeIn",
        "ManualCreate",
        "FactoryCreate",
        "OrderCreate",
        "ShareIn",
    ):
        assert schemas[name]["examples"], f"{name} should have a realistic sample"

    assert spec["paths"]["/api/v1/dashboard/{factory_id}"]["get"]["summary"]
    assert spec["paths"]["/api/v1/stress-tests"]["post"]["summary"]
    assert spec["paths"]["/api/v1/matching/search"]["post"]["summary"]
    assert spec["paths"]["/api/v1/recovery-requests"]["post"]["summary"]
