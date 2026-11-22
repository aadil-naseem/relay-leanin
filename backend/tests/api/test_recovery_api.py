"""Phase 11: M7/M9/M10 recovery request, handover pack, tracking stepper.

Section 9 demo steps 5-6 through the API: prefill from a stress test, ranked
options (Ready / Approval Pending / Excluded), select the Ready partner,
handover pack, stepper. Mocks are labelled SIMULATED SAMPLE and the handover
is consent-aware (redacted without FULL consent).
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.core import clock
from app.demo_seed import reset_demo

FROZEN = datetime(2026, 11, 14, 9, 0, 0, tzinfo=timezone.utc)

EXPECTED_STEPS = [
    "REQUEST_SENT",
    "PARTNER_RESPONSE",
    "TECHNICAL_AND_CUSTOMER_APPROVALS",
    "PRODUCTION_SCHEDULED",
    "PRODUCTION_STARTED",
    "QUALITY_INSPECTION",
    "DISPATCH_AND_DELIVERY",
]


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    from app.main import create_app

    with clock.frozen_time(FROZEN):
        reset_demo()
        with TestClient(create_app()) as test_client:
            yield test_client


def _make_stress(client) -> tuple[str, str]:
    """Manual FLOOD test on the owner; returns (stress_test_id, the hero order id)."""
    response = client.post(
        "/api/v1/stress-tests",
        json={
            "factory_id": "fac_owner",
            "hazard": "FLOOD",
            "scope": {"type": "sites", "ids": ["fac_owner"]},
            "start_in_hours": 24,
            "duration_hours": 72,
        },
    )
    assert response.status_code in (200, 201), response.text
    body = response.json()
    order_ids = {order["order_id"] for order in body["orders"]}
    assert "ord_102" in order_ids  # the PRT-B hero order is always simulated
    return body["id"], "ord_102"


def _prefill(client, stress_id: str, order_id: str) -> dict:
    response = client.post(
        "/api/v1/recovery-requests",
        json={"from_stress_test_id": stress_id, "order_id": order_id},
    )
    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------------- prefill


def test_prefill_from_stress_test(client):
    stress_id, order_id = _make_stress(client)
    body = _prefill(client, stress_id, order_id)

    assert body["factory_id"] == "fac_owner"
    assert body["order_id"] == order_id
    assert body["stress_test_id"] == stress_id
    assert body["status"] == "OPEN"
    assert body["selected_partner_id"] is None
    assert body["data_label"] == "SIMULATED SAMPLE"
    assert "human, customer and contractual approvals" in body["activation_note"]

    # the seven tracking steps exist, all PENDING, in the fixed order
    tracking = client.get(f"/api/v1/recovery-requests/{body['id']}/tracking").json()
    assert [step["step_key"] for step in tracking["steps"]] == EXPECTED_STEPS
    assert all(step["state"] == "PENDING" for step in tracking["steps"])

    # options carry the section 9 story: Ready hero, Approval Pending, Excluded
    by_partner = {option["partner_id"]: option for option in body["options"]}
    assert by_partner["fac_oragadam"]["status"] == "READY"
    assert by_partner["fac_oragadam"]["excluded"] is False
    assert by_partner["fac_hosur"]["status"] == "APPROVAL_PENDING"
    assert "CUSTOMER_APPROVED pending" in by_partner["fac_hosur"]["outstanding_checks"]
    assert "CAPACITY_RECONFIRMED pending" in by_partner["fac_hosur"]["outstanding_checks"]
    assert by_partner["fac_amb_nb"]["excluded"] is True
    assert by_partner["fac_amb_nb"]["exclusion_reason"] in ("SAME_CLUSTER", "SAME_HAZARD_ZONE")
    assert by_partner["fac_guindy"]["excluded"] is True
    assert by_partner["fac_guindy"]["exclusion_reason"] == "ALSO_EXPOSED_SAME_EVENT"
    # capacity summaries are declared data, labelled as such
    assert "declared spare" in by_partner["fac_oragadam"]["capacity_summary"]


def test_manual_creation_and_validation_errors(client):
    manual = client.post(
        "/api/v1/recovery-requests", json={"factory_id": "fac_owner", "order_id": "ord_102"}
    )
    assert manual.status_code == 201
    assert manual.json()["stress_test_id"] is None

    incomplete = client.post("/api/v1/recovery-requests", json={"order_id": "ord_102"})
    assert incomplete.status_code == 422
    assert incomplete.json()["error"]["code"] == "VALIDATION_ERROR"

    unknown_stress = client.post(
        "/api/v1/recovery-requests",
        json={"from_stress_test_id": "str_nope", "order_id": "ord_102"},
    )
    assert unknown_stress.status_code == 404

    unknown_order = client.post(
        "/api/v1/recovery-requests", json={"factory_id": "fac_owner", "order_id": "ord_nope"}
    )
    assert unknown_order.status_code == 404

    wrong_factory = client.post(
        "/api/v1/recovery-requests", json={"factory_id": "fac_oragadam", "order_id": "ord_102"}
    )
    assert wrong_factory.status_code == 409
    assert wrong_factory.json()["error"]["code"] == "ORDER_NOT_IN_FACTORY"


# ---------------------------------------------------------------- selection guards


def test_cannot_select_excluded_partner(client):
    stress_id, order_id = _make_stress(client)
    body = _prefill(client, stress_id, order_id)

    for partner_id, reason in (("fac_amb_nb", "SAME_CLUSTER"), ("fac_guindy", "ALSO_EXPOSED_SAME_EVENT")):
        response = client.post(
            f"/api/v1/recovery-requests/{body['id']}/select-partner", json={"partner_id": partner_id}
        )
        assert response.status_code == 409
        error = response.json()["error"]
        assert error["code"] == "EXCLUDED_PARTNER"
        assert error["details"]["exclusion_reason"] == reason


def test_cannot_select_incapable_partner(client):
    """Hosur is viable but fails the +-0.005 grinding filter for PRT-A (ord_101)."""
    stress_id, _order_id = _make_stress(client)
    body = _prefill(client, stress_id, "ord_101")

    response = client.post(
        f"/api/v1/recovery-requests/{body['id']}/select-partner", json={"partner_id": "fac_hosur"}
    )
    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "NOT_CAPABLE"
    assert error["details"]["failed_filters"]


def test_unknown_partner_is_404(client):
    stress_id, order_id = _make_stress(client)
    body = _prefill(client, stress_id, order_id)
    response = client.post(
        f"/api/v1/recovery-requests/{body['id']}/select-partner", json={"partner_id": "fac_nope"}
    )
    assert response.status_code == 404


# ---------------------------------------------------------------- selection + stepper


def test_select_ready_partner_then_stepper_order(client):
    stress_id, order_id = _make_stress(client)
    body = _prefill(client, stress_id, order_id)

    selected = client.post(
        f"/api/v1/recovery-requests/{body['id']}/select-partner", json={"partner_id": "fac_oragadam"}
    )
    assert selected.status_code == 200, selected.text
    selected_body = selected.json()
    assert selected_body["selected_partner_id"] == "fac_oragadam"
    assert selected_body["status"] == "ACTIVE"
    assert selected_body["outstanding_approvals"] == []  # Oragadam's checks are all done

    # REQUEST_SENT is already DONE; every advance moves exactly one step
    tracking = client.get(f"/api/v1/recovery-requests/{body['id']}/tracking").json()
    states = [(step["step_key"], step["state"]) for step in tracking["steps"]]
    assert states[0] == ("REQUEST_SENT", "DONE")
    assert all(state == "PENDING" for _key, state in states[1:])
    assert tracking["data_label"] == "SIMULATED SAMPLE"

    for expected_key in EXPECTED_STEPS[1:]:
        advanced = client.post(f"/api/v1/recovery-requests/{body['id']}/tracking/advance")
        assert advanced.status_code == 200
        steps = {step["step_key"]: step["state"] for step in advanced.json()["steps"]}
        assert steps[expected_key] == "DONE"
        # steps before it stay DONE, steps after stay PENDING
        index = EXPECTED_STEPS.index(expected_key)
        assert all(steps[key] == "DONE" for key in EXPECTED_STEPS[: index + 1])
        assert all(steps[key] == "PENDING" for key in EXPECTED_STEPS[index + 1 :])

    done = client.post(f"/api/v1/recovery-requests/{body['id']}/tracking/advance")
    assert done.status_code == 409
    assert done.json()["error"]["code"] == "ALL_STEPS_DONE"

    # selection is idempotent for the same partner, guarded otherwise
    again = client.post(
        f"/api/v1/recovery-requests/{body['id']}/select-partner", json={"partner_id": "fac_oragadam"}
    )
    assert again.status_code == 200
    switch = client.post(
        f"/api/v1/recovery-requests/{body['id']}/select-partner", json={"partner_id": "fac_hosur"}
    )
    assert switch.status_code == 409
    assert switch.json()["error"]["code"] == "ALREADY_SELECTED"


# ---------------------------------------------------------------- handover


def test_handover_redacted_without_consent(client):
    """No passport share -> the pack must not carry identifying fields (task 5)."""
    stress_id, order_id = _make_stress(client)
    body = _prefill(client, stress_id, "ord_102")  # PRT-B pump shaft
    client.post(f"/api/v1/recovery-requests/{body['id']}/select-partner", json={"partner_id": "fac_oragadam"})

    pack = client.get(f"/api/v1/recovery-requests/{body['id']}/handover").json()
    assert pack["data_label"] == "SIMULATED SAMPLE"
    assert pack["quantity"] == 200
    flat = str(pack)
    # redacted fields: drawing number, part name, customer alias
    assert "DWG-PSH-014" not in flat
    assert "Pump shaft" not in flat
    assert "ACME" not in flat
    assert pack["job_requirements"]["job"] != "Pump shaft"
    assert pack["job_requirements"]["material"] == "EN8"
    assert [step["process"] for step in pack["job_requirements"]["process_route"]] == ["TURN", "MILL"]

    # the rendered text carries the labels and the activation disclaimer
    assert "SIMULATED SAMPLE" in pack["text"]
    assert "human, customer and contractual approvals" in pack["text"]
    assert "Customer approval for alternate production source" in pack["required_approvals"]
    assert len(pack["milestones"]) == 7
    assert pack["milestones"][0]["step_key"] == "REQUEST_SENT"


def test_handover_full_consent_releases_documents(client):
    """A FULL passport share authorises the passport and drawing in the pack."""
    from sqlalchemy.orm import Session

    from app.db import engine
    from app.enums import PassportStatus, ShareLevel
    from app.models import Passport, PassportShare

    stress_id, _order_id = _make_stress(client)
    body = _prefill(client, stress_id, "ord_102")
    client.post(f"/api/v1/recovery-requests/{body['id']}/select-partner", json={"partner_id": "fac_oragadam"})

    with Session(engine) as session:
        passport = Passport(id="pas_test", part_id="prt_b", status=PassportStatus.CONFIRMED, data={})
        session.add(passport)
        session.commit()
        request = client.get(f"/api/v1/recovery-requests/{body['id']}").json()
        _ = request  # passport_id on the request is set at creation; attach now via update
        session.add(
            PassportShare(id="sh_test", passport_id="pas_test", partner_id="fac_oragadam", level=ShareLevel.FULL)
        )
        session.commit()

    # link the passport to the request (creation happened before the passport existed)
    from sqlalchemy import update

    from app.models import RecoveryRequest as RR

    with Session(engine) as session:
        session.execute(update(RR).where(RR.id == body["id"]).values(passport_id="pas_test"))
        session.commit()

    pack = client.get(f"/api/v1/recovery-requests/{body['id']}/handover").json()
    assert "Production passport pas_test" in pack["authorised_documents"]
    assert "Drawing DWG-PSH-014" in pack["authorised_documents"]
    assert pack["job_requirements"]["job"] == "Pump shaft"  # FULL consent releases the part name


def test_handover_and_advance_require_selection(client):
    manual = client.post(
        "/api/v1/recovery-requests", json={"factory_id": "fac_owner", "order_id": "ord_102"}
    ).json()
    handover = client.get(f"/api/v1/recovery-requests/{manual['id']}/handover")
    assert handover.status_code == 409
    assert handover.json()["error"]["code"] == "NO_PARTNER_SELECTED"

    advance = client.post(f"/api/v1/recovery-requests/{manual['id']}/tracking/advance")
    assert advance.status_code == 409
    assert advance.json()["error"]["code"] == "NO_PARTNER_SELECTED"


def test_unknown_request_404(client):
    assert client.get("/api/v1/recovery-requests/rr_nope").status_code == 404
    assert client.get("/api/v1/recovery-requests/rr_nope/handover").status_code == 404
    assert client.get("/api/v1/recovery-requests/rr_nope/tracking").status_code == 404