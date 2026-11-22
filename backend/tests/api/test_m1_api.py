"""Phase 5: M1 API tests (section 8) against the seeded demo world.

Covers: factory/machine/order CRUD, machine count=N -> N rows, guarded status
transitions (409 with details.missing_checks), check completion, reconfirm,
STALE computed at read time, and the uniform error envelope everywhere.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.core import clock
from app.demo_seed import reset_demo


@pytest.fixture()
def seeded():
    frozen = datetime(2026, 11, 14, 9, 0, 0, tzinfo=timezone.utc)
    with clock.frozen_time(frozen):
        reset_demo()
    return frozen


@pytest.fixture()
def client(seeded):
    from fastapi.testclient import TestClient

    from app.main import create_app

    with clock.frozen_time(seeded), TestClient(create_app()) as test_client:
        yield test_client


# ---------------------------------------------------------------- factories


def test_get_factories_returns_seeded_world(client):
    response = client.get("/api/v1/factories")
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 7
    owner = next(item for item in items if item["id"] == "fac_owner")
    assert owner["role"] == "OWNER"
    assert owner["is_sample"] is True  # R9: demo data labelled


def test_create_and_update_factory_round_trip(client):
    payload = {
        "role": "PARTNER",
        "name": "Test Works (SAMPLE)",
        "lat": 12.9,
        "lon": 80.1,
        "cluster_id": "cl_test",
    }
    response = client.post("/api/v1/factories", json=payload)
    assert response.status_code == 201
    created = response.json()
    assert created["id"].startswith("fac_")
    assert created["is_sample"] is True

    put = client.put(f"/api/v1/factories/{created['id']}", json={"name": "Renamed (SAMPLE)"})
    assert put.status_code == 200
    assert put.json()["name"] == "Renamed (SAMPLE)"
    assert put.json()["cluster_id"] == "cl_test"  # unset fields unchanged

    got = client.get(f"/api/v1/factories/{created['id']}")
    assert got.status_code == 200 and got.json()["name"] == "Renamed (SAMPLE)"


def test_factory_error_shapes_use_the_envelope(client):
    missing = client.post("/api/v1/factories", json={"name": "incomplete"})
    assert missing.status_code == 422
    body = missing.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "details" in body["error"]

    unknown = client.get("/api/v1/factories/fac_nope")
    assert unknown.status_code == 404
    assert unknown.json()["error"]["code"] == "NOT_FOUND"


# ---------------------------------------------------------------- machines


def test_machine_count_creates_n_rows(client):
    payload = {"process": "TURN", "name": "Test lathe", "count": 3, "achievable_tolerance_mm": 0.02}
    created = client.post("/api/v1/factories/fac_oragadam/machines", json=payload)
    assert created.status_code == 201
    machines = created.json()
    assert len(machines) == 3  # section 7.1: two lathes are never an SPOF
    assert len({m["id"] for m in machines}) == 3

    listed = client.get("/api/v1/factories/fac_oragadam/machines")
    assert listed.status_code == 200
    assert len(listed.json()["items"]) == 6 + 3  # 6 seeded + 3 new


def test_machine_update_and_delete(client):
    created = client.post(
        "/api/v1/factories/fac_owner/machines",
        json={"process": "MILL", "name": "Temp VMC", "count": 1},
    )
    machine_id = created.json()[0]["id"]

    put = client.put(f"/api/v1/machines/{machine_id}", json={"name": "Renamed VMC", "available": False})
    assert put.status_code == 200
    assert put.json()["name"] == "Renamed VMC"
    assert put.json()["available"] is False
    assert put.json()["process"] == "MILL"  # untouched fields survive

    delete = client.delete(f"/api/v1/machines/{machine_id}")
    assert delete.status_code == 204
    # PUT on the deleted id is now 404 (section 8 has no GET /machines/{id})
    assert client.put(f"/api/v1/machines/{machine_id}", json={"name": "x"}).status_code == 404
    assert client.put("/api/v1/machines/mch_nope", json={"name": "x"}).status_code == 404


# ---------------------------------------------------------------- parts + orders


def test_list_parts_for_owner(client):
    response = client.get("/api/v1/factories/fac_owner/parts")
    assert response.status_code == 200
    parts = response.json()["items"]
    assert len(parts) == 6
    assert {p["id"] for p in parts} == {f"prt_{c}" for c in "abcdef"}


def test_create_order_validations(client):
    ok = client.post(
        "/api/v1/factories/fac_owner/orders",
        json={"part_id": "prt_b", "qty": 10, "due_at": "2026-11-20T12:00:00Z", "value_inr": 50000.0},
    )
    assert ok.status_code == 201
    assert ok.json()["id"].startswith("ord_")

    bad_part = client.post(
        "/api/v1/factories/fac_owner/orders",
        json={"part_id": "prt_nope", "qty": 10, "due_at": "2026-11-20T12:00:00Z", "value_inr": 1.0},
    )
    assert bad_part.status_code == 404
    assert bad_part.json()["error"]["code"] == "NOT_FOUND"

    wrong_factory = client.post(
        "/api/v1/factories/fac_oragadam/orders",
        json={"part_id": "prt_b", "qty": 10, "due_at": "2026-11-20T12:00:00Z", "value_inr": 1.0},
    )
    assert wrong_factory.status_code == 409
    assert wrong_factory.json()["error"]["code"] == "PART_NOT_IN_FACTORY"

    bad_value = client.post(
        "/api/v1/factories/fac_owner/orders",
        json={"part_id": "prt_b", "qty": 0, "due_at": "2026-11-20T12:00:00Z", "value_inr": -1.0},
    )
    assert bad_value.status_code == 422

    listed = client.get("/api/v1/factories/fac_owner/orders")
    assert len(listed.json()["items"]) == 9  # 8 seeded + 1 new


def test_orders_filter_by_part(client):
    response = client.get("/api/v1/factories/fac_owner/orders", params={"part_id": "prt_b"})
    assert response.status_code == 200
    assert all(o["part_id"] == "prt_b" for o in response.json()["items"])
    assert len(response.json()["items"]) == 2  # ord_102 + ord_107


# ---------------------------------------------------------------- relationships


def test_relationship_effective_status_is_computed_at_read_time(client, seeded):
    response = client.get("/api/v1/factories/fac_owner/relationships")
    assert response.status_code == 200
    by_partner = {r["partner_id"]: r for r in response.json()}
    # Peenya is READY but confirmed ~120 days ago -> reads STALE, never stored
    assert by_partner["fac_peenya"]["status"] == "READY"
    assert by_partner["fac_peenya"]["effective_status"] == "STALE"
    assert by_partner["fac_oragadam"]["effective_status"] == "READY"
    assert by_partner["fac_hosur"]["status"] == "APPROVAL_PENDING"
    assert by_partner["fac_hosur"]["effective_status"] == "APPROVAL_PENDING"
    # stored status never contains STALE
    assert all(r["status"] != "STALE" for r in by_partner.values())


def test_guarded_transition_blocks_ready_without_checks(client):
    response = client.patch(
        "/api/v1/relationships/rel_hosur/status", json={"status": "READY"}
    )
    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "MISSING_CHECKS"
    assert set(body["error"]["details"]["missing_checks"]) == {
        "CAPACITY_RECONFIRMED",
        "CUSTOMER_APPROVED",
    }
    # the stored status did not change
    assert client.get("/api/v1/relationships/rel_hosur").json()["status"] == "APPROVAL_PENDING"


def test_approval_pending_requires_only_tech_assessment(client):
    # rel_cbe is POTENTIAL_MATCH with only TECH done -> APPROVAL_PENDING is legal
    response = client.patch(
        "/api/v1/relationships/rel_cbe/status", json={"status": "APPROVAL_PENDING"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "APPROVAL_PENDING"


def test_unavailable_expired_allowed_from_any_state(client):
    response = client.patch(
        "/api/v1/relationships/rel_amb_nb/status", json={"status": "UNAVAILABLE_EXPIRED"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "UNAVAILABLE_EXPIRED"


def test_complete_checks_then_ready(client, seeded):
    for key in ("CAPACITY_RECONFIRMED", "CUSTOMER_APPROVED"):
        done = client.post(f"/api/v1/relationships/rel_hosur/checks/{key}/complete")
        assert done.status_code == 200
        assert next(c for c in done.json()["checks"] if c["key"] == key)["done"] is True

    ready = client.patch("/api/v1/relationships/rel_hosur/status", json={"status": "READY"})
    assert ready.status_code == 200
    assert ready.json()["status"] == "READY"
    assert ready.json()["effective_status"] == "READY"


def test_capacity_reconfirm_and_reconfirm_refresh_last_confirmed(client, seeded):
    before = client.get("/api/v1/relationships/rel_peenya").json()
    assert before["effective_status"] == "STALE"

    reconfirmed = client.post("/api/v1/relationships/rel_peenya/reconfirm")
    assert reconfirmed.status_code == 200
    confirmed_at = datetime.fromisoformat(reconfirmed.json()["last_confirmed_at"])
    assert confirmed_at == seeded

    after = client.get("/api/v1/relationships/rel_peenya").json()
    assert after["effective_status"] == "READY"  # staleness cured by reconfirm


def test_relationship_404_uses_the_envelope(client):
    assert client.get("/api/v1/relationships/rel_nope").status_code == 404
    body = client.patch("/api/v1/relationships/rel_nope/status", json={"status": "READY"}).json()
    assert body["error"]["code"] == "NOT_FOUND"
