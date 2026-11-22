"""Phase 10: M8 readiness API against the seeded demo world - section 9 invariants 5 and 6.

Invariant 5: Peenya is READY but effective STALE and does not count.
Invariant 6: initial readiness (48 h) is between 30 and 55; after completing
Hosur's two missing checks and setting it READY, the score rises by >= 10.
Also: the actions uplift equals the real delta when the action is executed.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.core import clock
from app.demo_seed import reset_demo

FROZEN = datetime(2026, 11, 14, 9, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    from app.main import create_app

    with clock.frozen_time(FROZEN):
        reset_demo()
        with TestClient(create_app()) as test_client:
            yield test_client


def _readiness(client):
    return client.get("/api/v1/readiness/fac_owner").json()


def _actions(client):
    return client.get("/api/v1/readiness/fac_owner/actions").json()


def _complete_hosur_and_ready(client):
    for key in ("CAPACITY_RECONFIRMED", "CUSTOMER_APPROVED"):
        response = client.post("/api/v1/relationships/rel_hosur/checks/{key}/complete".format(key=key))
        assert response.status_code == 200
    response = client.patch("/api/v1/relationships/rel_hosur/status", json={"status": "READY"})
    assert response.status_code == 200


# ---------------------------------------------------------------- invariant 6


def test_initial_score_in_range_and_rises_after_hosur(client):
    before = _readiness(client)
    assert before["window_hours"] == 48
    assert 30 <= before["weighted_score"] <= 55, before["weighted_score"]

    windows = {w["window_hours"]: w for w in before["windows"]}
    # monotone in the window: relaxed constraints can only add coverage
    assert windows[24]["weighted_score"] <= windows[48]["weighted_score"] <= windows[72]["weighted_score"]

    _complete_hosur_and_ready(client)
    after = _readiness(client)
    delta = after["weighted_score"] - before["weighted_score"]
    assert delta >= 10, delta
    # unweighted rises too (2 -> 3 of 4 critical parts)
    assert after["score"] - before["score"] >= 10

    # PRT-F is now covered by Hosur
    prt_f = next(item for item in after["breakdown"] if item["part_id"] == "prt_f")
    assert prt_f["covered"] is True
    assert prt_f["covered_by"] == "fac_hosur"


def test_breakdown_reasons_match_the_story(client):
    body = _readiness(client)
    by_part = {item["part_id"]: item for item in body["breakdown"]}
    # PRT-A: nobody owns grinder + heat together -> honest gap
    assert by_part["prt_a"]["covered"] is False
    assert by_part["prt_a"]["reason"] == "NO_PARTNER_ELIGIBLE"
    # hero + valve flange covered by Oragadam
    assert by_part["prt_b"]["covered"] is True and by_part["prt_b"]["covered_by"] == "fac_oragadam"
    assert by_part["prt_c"]["covered"] is True and by_part["prt_c"]["covered_by"] == "fac_oragadam"
    # Hosur-dependent part waits for approvals
    assert by_part["prt_f"]["reason"] == "NOT_READY"
    # weights = open order values
    assert by_part["prt_a"]["weight_inr"] == pytest.approx(1_200_000.0)
    assert by_part["prt_b"]["weight_inr"] == pytest.approx(1_270_000.0)  # ord_102 + ord_107


# ---------------------------------------------------------------- invariant 5


def test_stale_peenya_does_not_count(client):
    body = _readiness(client)
    assert body["stale_partners"] == 1
    review = {item["partner_id"]: item for item in body["review"]}
    assert review["fac_peenya"]["effective_status"] == "STALE"
    assert review["fac_peenya"]["days_since_confirm"] == pytest.approx(120.0)
    # no critical part is covered by Peenya while stale
    assert all(item["covered_by"] != "fac_peenya" for item in body["breakdown"])


def test_reconfirming_peenya_does_not_change_the_score(client):
    """Peenya covers nothing new even when fresh - uplift must be 0 (invariant 5)."""
    before = _readiness(client)
    actions_before = {a["partner_id"]: a["uplift_points"] for a in _actions(client)["actions"]}
    assert "fac_peenya" not in actions_before  # zero-gain actions are omitted

    reconfirmed = client.post("/api/v1/relationships/rel_peenya/reconfirm")
    assert reconfirmed.status_code == 200

    after = _readiness(client)
    assert after["stale_partners"] == 0  # it is now fresh
    assert after["weighted_score"] == pytest.approx(before["weighted_score"])  # but the score did not move


# ---------------------------------------------------------------- actions


def test_top_action_uplift_equals_the_real_delta(client):
    """Done-when: the predicted uplift equals the real change when executed."""
    actions = _actions(client)["actions"]
    assert actions, "the seeded world must have at least one positive-gain action"
    top = actions[0]
    assert top["partner_id"] == "fac_hosur"
    assert top["uplift_points"] == pytest.approx(top["projected_score"] - top["current_score"])
    projected = top["projected_score"]

    _complete_hosur_and_ready(client)
    after = _readiness(client)
    assert after["weighted_score"] == pytest.approx(projected)  # prediction == reality
    assert after["weighted_score"] - top["current_score"] == pytest.approx(top["uplift_points"])


def test_actions_endpoints_shapes(client):
    body = _actions(client)
    assert body["window_hours"] == 48
    for action in body["actions"]:
        assert action["label"]
        assert action["uplift_points"] > 0
        assert set(action) >= {"relationship_id", "partner_id", "label", "uplift_points", "current_score", "projected_score"}
    assert len(body["actions"]) <= 5  # top 5 by gain


# ---------------------------------------------------------------- snapshots + history


def test_history_records_computations_and_excludes_initial(client):
    empty = client.get("/api/v1/readiness/fac_owner/history").json()
    assert empty["points"] == []  # the INITIAL row is not a computed score

    _readiness(client)
    first = client.get("/api/v1/readiness/fac_owner/history").json()["points"]
    assert first, "a readiness call must write snapshots"
    assert {point["window_hours"] for point in first} == {24, 48, 72}

    _complete_hosur_and_ready(client)  # status changes write snapshots too
    second = client.get("/api/v1/readiness/fac_owner/history").json()["points"]
    assert len(second) > len(first)
    # the last 48 h point reflects the improved score
    last_48 = [p for p in second if p["window_hours"] == 48][-1]
    assert last_48["weighted_score"] == pytest.approx(_readiness(client)["weighted_score"])


def test_invalid_window_and_partner_factory(client):
    assert client.get("/api/v1/readiness/fac_owner", params={"window": 7}).status_code == 422
    response = client.get("/api/v1/readiness/fac_oragadam")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "NOT_AN_OWNER"
    assert client.get("/api/v1/readiness/fac_nope").status_code == 404


def test_trace_explains_the_windows(client):
    body = _readiness(client)
    steps = [entry["step"] for entry in body["trace"]]
    assert steps[0] == "load_world"
    assert steps.count("window") == 3
    risk_entries = [entry for entry in body["trace"] if entry["step"] == "window"]
    assert all("weighted" in entry["detail"] for entry in risk_entries)