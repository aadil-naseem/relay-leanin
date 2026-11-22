"""M7/M9/M10 schemas: recovery requests (manual or alert-prefilled), options, mocks."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.enums import BackupStatus, EffectiveStatus


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _Out(BaseModel):
    model_config = ConfigDict(extra="forbid")


DATA_LABEL = "SIMULATED SAMPLE"


class RecoveryCreate(_In):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {"from_stress_test_id": "str_auto_sample", "order_id": "ord_102"},
                {"factory_id": "fac_owner", "order_id": "ord_102"},
            ]
        },
    )

    # Prefill from an alert: both ids required together (section 7.3).
    from_stress_test_id: str | None = None
    order_id: str | None = None
    # Manual creation needs the factory context instead.
    factory_id: str | None = None


class OptionOut(_Out):
    partner_id: str
    name: str
    status: BackupStatus
    effective_status: EffectiveStatus
    excluded: bool = False
    exclusion_reason: str | None = None
    outstanding_checks: list[str] = []  # e.g. ["CUSTOMER_APPROVED pending"]
    capacity_summary: str | None = None


class RecoveryOut(_Out):
    id: str
    factory_id: str
    order_id: str
    stress_test_id: str | None
    passport_id: str | None
    status: str
    selected_partner_id: str | None
    options: list[OptionOut] = []
    outstanding_approvals: list[str] = []
    data_label: str = DATA_LABEL
    activation_note: str = ""
    created_at: datetime


class SelectPartnerIn(_In):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"partner_id": "fac_oragadam"}]},
    )

    partner_id: str


class HandoverOut(_Out):
    request_id: str
    data_label: str = DATA_LABEL
    job_requirements: dict
    authorised_documents: list[str]
    quantity: int
    deadline: datetime
    inspection_checklist: list[str]
    responsibilities: list[dict]
    required_approvals: list[str]
    milestones: list[dict]
    text: str = ""  # the same pack rendered as markdown (Jinja2)


class StepOut(_Out):
    step_key: str
    state: str  # PENDING | DONE
    at: datetime | None


class TrackingOut(_Out):
    request_id: str
    data_label: str = DATA_LABEL
    steps: list[StepOut]
