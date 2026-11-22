"""Phase 12: M2 passport API tests. NO network - Gemini is mocked with respx.

Covers: golden-cache extraction (< 3 s), provider failure -> rules draft,
retry-on-5xx, 429 cooldown, manual create, PATCH -> CONFIRMED, confirm guard,
confirm creates part + steps, RFQ leak test across all fixtures, consent gate.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest
import respx

from app.adapters.vision import cache as golden_cache
from app.adapters.vision import gemini as gemini_provider
from app.core import clock
from app.demo_seed import reset_demo

BACKEND_DIR = Path(__file__).resolve().parents[2]
DRAWINGS_DIR = BACKEND_DIR / "data" / "drawings"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent"

FROZEN = datetime(2026, 11, 14, 9, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def client(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient

    from app.main import create_app

    # tests can never pollute the committed golden cache or reach the real API
    monkeypatch.setenv("FCD_GOLDEN_WRITE_DIR", str(tmp_path / "golden"))
    monkeypatch.setattr(gemini_provider, "available", lambda: False)
    with clock.frozen_time(FROZEN):
        reset_demo()
        with TestClient(create_app()) as test_client:
            yield test_client


@pytest.fixture()
def allow_mocked_gemini(monkeypatch):
    """Re-enable the provider so transport-mocked tests can drive it.

    The patched available() still honours the quota cooldown, exactly like the
    real gate minus the key check (the key exists in tests).
    """
    import time

    monkeypatch.setattr(
        gemini_provider, "available", lambda: time.monotonic() >= gemini_provider._cooldown_until
    )


@pytest.fixture()
def png_bytes():
    return (DRAWINGS_DIR / "pump_shaft.png").read_bytes()


# ---------------------------------------------------------------- extraction


def test_cached_extraction_is_fast_and_labelled(client, png_bytes):
    """The golden file for this PNG is committed; extraction must be < 3 s."""
    started = time.perf_counter()
    response = client.post(
        "/api/v1/passports/extract",
        files={"file": ("pump_shaft.png", png_bytes, "image/png")},
    )
    elapsed = time.perf_counter() - started
    assert response.status_code == 200
    body = response.json()
    assert elapsed < 3.0
    assert body["extraction_meta"]["provider"] == "cache"
    assert body["extraction_meta"]["sha256"] == golden_cache.sha256_of(png_bytes)
    assert body["extraction_meta"]["degraded"] is False
    assert body["status"] == "DRAFT"
    assert body["data"]["quantity"]["value"] == 200


def test_pdf_extract_with_vision_failure_falls_back_to_rules(client, allow_mocked_gemini):
    """No golden for the PDF + Gemini down -> rules-only draft, honestly labelled."""
    pdf_bytes = (DRAWINGS_DIR / "pump_shaft.pdf").read_bytes()
    with respx.mock() as mock:
        mock.post(GEMINI_URL).mock(side_effect=httpx.ConnectError("no network"))
        response = client.post(
            "/api/v1/passports/extract",
            files={"file": ("pump_shaft.pdf", pdf_bytes, "application/pdf")},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["extraction_meta"]["provider"] == "rules"
    assert body["extraction_meta"]["degraded"] is True
    assert any("rules-only" in warning for warning in body["extraction_meta"]["warnings"])
    # the text layer carried the title block: rules found the fields (MEDIUM)
    assert body["data"]["drawing_no"]["value"] == "DWG-PSH-014"
    assert body["data"]["drawing_no"]["confidence"] == "MEDIUM"
    assert body["data"]["quantity"]["value"] == 200


def test_vision_agreement_yields_high_confidence(client, allow_mocked_gemini):
    """PDF text + a mock vision response that agrees -> HIGH fields."""
    pdf_bytes = (DRAWINGS_DIR / "pump_shaft.pdf").read_bytes()
    vision = {
        "part_name": "PUMP SHAFT",
        "drawing_no": "DWG-PSH-014",
        "revision": "B",
        "customer": "ACME Pumps (SAMPLE)",
        "quantity": 200,
        "material": {"grade": "EN8", "standard": None, "form": None},
        "tightest_tolerance_mm": 0.02,
        "general_tolerance_standard": "ISO 2768-m",
        "surface_finish_ra_um": 1.6,
        "process_route": [{"process": "TURN"}, {"process": "MILL"}],
        "dimensions": None,
        "envelope_mm": 250.0,
    }
    with respx.mock() as mock:
        route = mock.post(GEMINI_URL).mock(return_value=httpx.Response(200, json={
            "candidates": [{"content": {"parts": [{"text": json.dumps(vision)}]}}]
        }))
        response = client.post(
            "/api/v1/passports/extract",
            files={"file": ("pump_shaft.pdf", pdf_bytes, "application/pdf")},
        )
    assert route.called
    body = response.json()
    assert body["extraction_meta"]["provider"] == "gemini"
    for key in ("drawing_no", "quantity", "material"):
        assert body["data"][key]["confidence"] == "HIGH", key
        assert body["data"][key]["source"] == "rules+vision"
    # the golden result for the PDF is now stored - a re-extract hits the cache
    again = client.post(
        "/api/v1/passports/extract",
        files={"file": ("pump_shaft.pdf", pdf_bytes, "application/pdf")},
    ).json()
    assert again["extraction_meta"]["provider"] == "cache"


def test_gemini_5xx_retried_once_then_rules_draft(client, allow_mocked_gemini):
    pdf_bytes = (DRAWINGS_DIR / "valve_flange.pdf").read_bytes()
    with respx.mock() as mock:
        route = mock.post(GEMINI_URL).mock(return_value=httpx.Response(503, json={"error": "busy"}))
        response = client.post(
            "/api/v1/passports/extract",
            files={"file": ("valve_flange.pdf", pdf_bytes, "application/pdf")},
        )
    assert route.call_count == 2  # one retry on 5xx
    body = response.json()
    assert body["extraction_meta"]["provider"] == "rules"
    assert body["data"]["material"]["value"]["grade"] == "SS304"


def test_gemini_429_starts_cooldown(client, allow_mocked_gemini):
    pdf_bytes = (DRAWINGS_DIR / "valve_flange.pdf").read_bytes()
    with respx.mock() as mock:
        route = mock.post(GEMINI_URL).mock(return_value=httpx.Response(429, json={"error": "quota"}))
        first = client.post(
            "/api/v1/passports/extract",
            files={"file": ("valve_flange.pdf", pdf_bytes, "application/pdf")},
        )
        assert first.json()["extraction_meta"]["provider"] == "rules"
        assert route.call_count == 1  # no retry on quota errors

        # inside the 10-minute cooldown the provider is not even called
        second = client.post(
            "/api/v1/passports/extract",
            files={"file": ("valve_flange.pdf", pdf_bytes, "application/pdf")},
        )
        assert route.call_count == 1
        assert second.json()["extraction_meta"]["provider"] == "rules"


def test_messy_image_without_text_layer_gives_empty_draft(client):
    """The rotated/low-contrast PNG has no text layer and no golden: empty draft.

    Gemini is disabled by the client fixture, so this is the honest
    no-text-layer fallback path (section 7.6 step 8).
    """
    messy = (DRAWINGS_DIR / "piston_rod_messy.png").read_bytes()
    response = client.post(
        "/api/v1/passports/extract",
        files={"file": ("piston_rod_messy.png", messy, "image/png")},
    )
    body = response.json()
    assert body["extraction_meta"]["provider"] == "rules"
    assert body["extraction_meta"]["degraded"] is True
    assert body["data"]["part_name"]["confidence"] == "MISSING"
    assert "process_route" in body["missing_required"]


# ---------------------------------------------------------------- manual + review


def test_manual_create_always_works(client):
    response = client.post(
        "/api/v1/passports/manual",
        json={
            "fields": {
                "part_name": "Test Bracket (SAMPLE)",
                "material": {"grade": "Al6061", "standard": None, "form": None},
                "quantity": 25,
                "process_route": [{"process": "MILL"}],
                "tightest_tolerance_mm": 0.1,
            }
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "DRAFT"
    for key in ("part_name", "material", "quantity"):
        assert body["data"][key]["confidence"] == "CONFIRMED"
        assert body["data"][key]["source"] == "user"

    empty = client.post("/api/v1/passports/manual", json={"fields": {}})
    assert empty.status_code == 422
    unknown = client.post("/api/v1/passports/manual", json={"fields": {"not_a_field": 1}})
    assert unknown.status_code == 201
    assert any("not_a_field" in w for w in unknown.json()["extraction_meta"]["warnings"])


def test_patch_makes_fields_confirmed(client, png_bytes):
    created = client.post(
        "/api/v1/passports/extract",
        files={"file": ("pump_shaft.png", png_bytes, "image/png")},
    ).json()
    passport_id = created["passport_id"]

    patched = client.patch(
        f"/api/v1/passports/{passport_id}", json={"data": {"deadline": "2026-11-30T12:00:00Z"}}
    )
    assert patched.status_code == 200
    deadline = patched.json()["data"]["deadline"]
    assert deadline["confidence"] == "CONFIRMED"
    assert deadline["source"] == "user"

    bad_field = client.patch(f"/api/v1/passports/{passport_id}", json={"data": {"nope": 1}})
    assert bad_field.status_code == 422


# ---------------------------------------------------------------- confirm


def _confirmable_manual(client) -> str:
    created = client.post(
        "/api/v1/passports/manual",
        json={
            "fields": {
                "part_name": "Confirm Shaft (SAMPLE)",
                "material": {"grade": "EN8", "standard": None, "form": None},
                "quantity": 10,
                "process_route": [{"process": "TURN"}, {"process": "MILL"}],
                "tightest_tolerance_mm": 0.02,
                "drawing_no": "DWG-TST-999",
            }
        },
    ).json()
    return created["id"]


def test_confirm_guard_blocks_incomplete_passport(client):
    created = client.post(
        "/api/v1/passports/manual", json={"fields": {"part_name": "Incomplete (SAMPLE)"}}
    ).json()
    response = client.post(f"/api/v1/passports/{created['id']}/confirm")
    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "MISSING_FIELDS"
    assert any("process_route" in item for item in error["details"]["missing"])
    assert any("material.grade" in item for item in error["details"]["missing"])


def test_confirm_creates_part_and_steps_with_default_cycle_times(client):
    passport_id = _confirmable_manual(client)
    response = client.post(f"/api/v1/passports/{passport_id}/confirm")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "CONFIRMED"
    assert body["part_id"]

    parts = client.get("/api/v1/factories/fac_owner/parts").json()["items"]
    part = next(p for p in parts if p["id"] == body["part_id"])
    assert part["name"] == "Confirm Shaft (SAMPLE)"
    assert part["material"] == "EN8"

    # default cycle times come from processes.yaml and are editable (section 7.6)
    from sqlalchemy.orm import Session

    from app.db import engine
    from app.models import PartStep

    with Session(engine) as session:
        steps = session.query(PartStep).filter(PartStep.part_id == part["id"]).order_by(PartStep.seq).all()
        assert [(s.seq, s.process.value) for s in steps] == [(1, "TURN"), (2, "MILL")]
        assert steps[0].hours_per_unit == pytest.approx(0.10)  # processes.yaml TURN default
        assert steps[1].tolerance_mm == pytest.approx(0.02)  # tightest tolerance on the last step

    again = client.post(f"/api/v1/passports/{passport_id}/confirm")
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "ALREADY_CONFIRMED"


def test_invalid_tolerance_is_not_trusted_by_confirm(client):
    """A vision 0.0 tolerance must not become a step tolerance (the merge flagged it LOW)."""
    created = client.post(
        "/api/v1/passports/manual",
        json={
            "fields": {
                "part_name": "Zero Tol (SAMPLE)",
                "material": {"grade": "EN8", "standard": None, "form": None},
                "quantity": 5,
                "process_route": [{"process": "TURN"}],
                "tightest_tolerance_mm": 0.0,
                "general_tolerance_standard": "ISO 2768-m",
            }
        },
    ).json()
    response = client.post(f"/api/v1/passports/{created['id']}/confirm")
    assert response.status_code == 200  # the general standard satisfies the guard
    from sqlalchemy.orm import Session

    from app.db import engine
    from app.models import PartStep

    with Session(engine) as session:
        steps = session.query(PartStep).filter(PartStep.part_id == created["part_id"] if False else PartStep.part_id == response.json()["part_id"]).all()
        assert all(step.tolerance_mm is None for step in steps)  # 0.0 is not a tolerance


# ---------------------------------------------------------------- RFQ + consent


def test_rfq_leak_test_across_fixtures(client, png_bytes):
    """Customer name, drawing number and part name never appear in RFQ JSON or text."""
    for filename, payload in (
        ("pump_shaft.png", png_bytes),
        ("pump_shaft.pdf", (DRAWINGS_DIR / "pump_shaft.pdf").read_bytes()),
    ):
        created = client.post(
            "/api/v1/passports/extract", files={"file": (filename, payload, "application/pdf")}
        ).json()
        passport_id = created["passport_id"]
        # confirm so the passport has a part with the identifying fields
        client.patch(
            f"/api/v1/passports/{passport_id}",
            json={"data": {"quantity": 200, "material": {"grade": "EN8", "standard": None, "form": None},
                           "process_route": [{"process": "TURN"}], "tightest_tolerance_mm": 0.02}},
        )
        client.post(f"/api/v1/passports/{passport_id}/confirm")

        rfq = client.get(f"/api/v1/passports/{passport_id}/rfq").json()
        flat = json.dumps(rfq) + rfq["text"]
        assert "DWG-PSH-014" not in flat, filename
        assert "Pump Shaft" not in flat and "PUMP SHAFT" not in flat, filename
        assert "ACME" not in flat, filename
        # the allow-list kept the technical content
        assert rfq["content"]["quantity"] == 200
        assert rfq["content"]["material"]["grade"] == "EN8"
        assert rfq["redaction_report"]["removed_keys"]
        assert rfq["rfq_ref"].startswith("RFQ-")
        assert rfq["rfq_ref"] in rfq["text"]
        # stable reference on re-fetch
        again = client.get(f"/api/v1/passports/{passport_id}/rfq").json()
        assert again["rfq_ref"] == rfq["rfq_ref"]


def test_deadline_becomes_days_from_now(client):
    passport_id = _confirmable_manual(client)
    client.patch(
        f"/api/v1/passports/{passport_id}", json={"data": {"deadline": "2026-11-16T09:00:00Z"}}
    )
    client.post(f"/api/v1/passports/{passport_id}/confirm")
    rfq = client.get(f"/api/v1/passports/{passport_id}/rfq").json()
    assert rfq["deadline_days_from_now"] == pytest.approx(2.0, abs=0.1)  # frozen now = 2026-11-14 09:00


def test_consent_gate_returns_403(client, png_bytes):
    created = client.post(
        "/api/v1/passports/extract", files={"file": ("pump_shaft.png", png_bytes, "image/png")}
    ).json()
    passport_id = created["passport_id"]

    denied = client.get(f"/api/v1/passports/{passport_id}/rfq", params={"partner_id": "fac_hosur"})
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "FORBIDDEN"

    denied_passport = client.get(f"/api/v1/passports/{passport_id}", params={"partner_id": "fac_hosur"})
    assert denied_passport.status_code == 403

    # owner context (no partner_id) is allowed
    assert client.get(f"/api/v1/passports/{passport_id}").status_code == 200

    # RFQ-level share unlocks the RFQ but not the passport
    client.post(f"/api/v1/passports/{passport_id}/share", json={"partner_id": "fac_hosur", "level": "RFQ"})
    assert client.get(f"/api/v1/passports/{passport_id}/rfq", params={"partner_id": "fac_hosur"}).status_code == 200
    assert client.get(f"/api/v1/passports/{passport_id}", params={"partner_id": "fac_hosur"}).status_code == 403

    # FULL share unlocks both
    client.post(f"/api/v1/passports/{passport_id}/share", json={"partner_id": "fac_oragadam", "level": "FULL"})
    assert client.get(f"/api/v1/passports/{passport_id}", params={"partner_id": "fac_oragadam"}).status_code == 200


def test_unknown_passport_404(client):
    assert client.get("/api/v1/passports/pas_nope").status_code == 404
    assert client.get("/api/v1/passports/pas_nope/rfq").status_code == 404
