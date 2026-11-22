"""Phase 6: M3 SPOF API against the seeded demo world (section 9 invariant 3).

The seeded world must produce the story: the grinder and the heat-treat vendor
are the top SPOFs and both are flagged exposed; the three lathes never appear.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.core import clock
from app.demo_seed import reset_demo


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    from app.main import create_app

    frozen = datetime(2026, 11, 14, 9, 0, 0, tzinfo=timezone.utc)
    with clock.frozen_time(frozen):
        reset_demo()
        with TestClient(create_app()) as test_client:
            yield test_client


def test_seeded_world_top_spof_is_grinder_or_heat_vendor(client):
    response = client.get("/api/v1/factories/fac_owner/spof")
    assert response.status_code == 200
    body = response.json()

    assert body["items"], "the seeded world must have single points of failure"
    assert body["total_orders"] == 8

    top = body["items"][0]
    assert top["resource_id"] in {"mch_own_grind_1", "ven_heat"}, top
    assert top["exposed"] is True

    by_id = {item["resource_id"]: item for item in body["items"]}

    # the grinder is a SPOF and it is inside the owner's flood zone
    grinder = by_id["mch_own_grind_1"]
    assert grinder["exposed"] is True
    assert "ord_101" in grinder["orders_broken"]
    assert grinder["revenue_at_risk_inr"] >= 1_000_000

    # the heat-treat vendor covers both heat-treated parts: PRT-A and PRT-F
    heat = by_id["ven_heat"]
    assert heat["exposed"] is True
    assert set(heat["orders_broken"]) == {"ord_101", "ord_106"}
    assert heat["revenue_at_risk_inr"] == pytest.approx(1_900_000.0)

    # the sole EN24 supplier is a SPOF for PRT-A too
    assert "sup_steel" in by_id
    assert by_id["sup_steel"]["exposed"] is True


def test_three_lathes_never_appear(client):
    body = client.get("/api/v1/factories/fac_owner/spof").json()
    resource_ids = {item["resource_id"] for item in body["items"]}
    assert not {f"mch_own_turn_{i}" for i in (1, 2, 3)} & resource_ids
    assert not {f"mch_own_mill_{i}" for i in (1, 2)} & resource_ids  # 2 VMCs cover MILL
    # and no partner machine leaks into the owner's SPOF list
    assert not any(item["resource_id"].startswith("mch_ora") for item in body["items"])


def test_ranking_and_counts_are_consistent(client):
    body = client.get("/api/v1/factories/fac_owner/spof").json()
    revenues = [item["revenue_at_risk_inr"] for item in body["items"]]
    assert revenues == sorted(revenues, reverse=True)
    assert [item["rank"] for item in body["items"]] == list(range(1, len(body["items"]) + 1))
    for item in body["items"]:
        assert item["orders_broken"], item
        assert item["kind"] in {"machine", "vendor", "supplier"}


def test_uncovered_materials_are_reported_honestly(client):
    body = client.get("/api/v1/factories/fac_owner/spof").json()
    joined = " | ".join(body["uncovered_requirements"])
    # only EN24 has an approved supplier in the demo world; the rest are gaps
    for material in ("EN8", "SS304"):
        assert material in joined
    assert "EN24" not in joined


def test_graph_supports_the_ui(client):
    body = client.get("/api/v1/factories/fac_owner/spof").json()
    assert body["nodes"] and body["edges"]
    kinds = {node["kind"] for node in body["nodes"]}
    assert {"part", "step", "machine", "vendor", "supplier"} <= kinds
    assert any(edge["relation"] == "can_serve" for edge in body["edges"])
    assert any(edge["to_node"] == "mch_own_grind_1" for edge in body["edges"])


def test_trace_explains_the_calculation(client):
    body = client.get("/api/v1/factories/fac_owner/spof").json()
    steps = [entry["step"] for entry in body["trace"]]
    assert steps[:2] == ["load_world", "coverage"]
    assert "remove_resource" in steps
    assert steps[-1] == "rank"
    assert "zone membership" in body["trace"][0]["output"]["exposure_flag"]


def test_partner_factory_is_rejected_with_409(client):
    response = client.get("/api/v1/factories/fac_oragadam/spof")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "NOT_AN_OWNER"


def test_unknown_factory_is_404(client):
    response = client.get("/api/v1/factories/fac_nope/spof")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"