"""M1 schemas: factories (owner/partner), machines, parts, orders."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.enums import ProcessCode, Role


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")


class MachineCreate(_In):
    process: ProcessCode
    name: str
    achievable_tolerance_mm: float | None = None
    envelope_mm: float | None = None
    available: bool = True
    count: int = Field(default=1, ge=1)  # N identical rows are created (section 7.1)


class MachineOut(_Out):
    id: str
    factory_id: str
    process: ProcessCode
    name: str
    achievable_tolerance_mm: float | None = None
    envelope_mm: float | None = None
    available: bool


class MachineUpdate(_In):
    process: ProcessCode | None = None
    name: str | None = None
    achievable_tolerance_mm: float | None = None
    envelope_mm: float | None = None
    available: bool | None = None


class FactoryCreate(_In):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "role": "PARTNER",
                    "name": "Sample Partner Works",
                    "lat": 12.85,
                    "lon": 79.95,
                    "cluster_id": "cl_oragadam",
                    "grid_id": "grid_kanchi_south",
                    "materials_handled": ["EN8"],
                }
            ]
        },
    )

    role: Role
    name: str
    lat: float
    lon: float
    cluster_id: str
    hazard_zone_id: str | None = None
    grid_id: str | None = None
    shift_hours_per_day: float = 16.0
    materials_handled: list[str] = []
    typical_lead_time_hours: float | None = None
    mobilisation_hours: float | None = None
    spare_hours_per_week: dict[str, float] = {}
    contacts: list[str] = []


class FactoryUpdate(_In):
    name: str | None = None
    lat: float | None = None
    lon: float | None = None
    cluster_id: str | None = None
    hazard_zone_id: str | None = None
    grid_id: str | None = None
    shift_hours_per_day: float | None = None
    materials_handled: list[str] | None = None
    typical_lead_time_hours: float | None = None
    mobilisation_hours: float | None = None
    spare_hours_per_week: dict[str, float] | None = None
    contacts: list[str] | None = None


class FactoryOut(_Out):
    id: str
    role: Role
    name: str
    is_sample: bool
    lat: float
    lon: float
    cluster_id: str
    hazard_zone_id: str | None
    grid_id: str | None
    shift_hours_per_day: float
    materials_handled: list[str]
    typical_lead_time_hours: float | None
    mobilisation_hours: float | None
    spare_hours_per_week: dict[str, float]
    contacts: list[str]


class PartOut(_Out):
    id: str
    factory_id: str
    name: str
    drawing_no: str | None
    customer_alias: str | None
    material: str
    is_critical: bool
    typical_batch_qty: int
    passport_id: str | None


class OrderCreate(_In):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "part_id": "prt_b",
                    "qty": 200,
                    "due_at": "2026-11-20T09:00:00Z",
                    "value_inr": 850000,
                    "customer_alias": "SAMPLE CUSTOMER",
                }
            ]
        },
    )

    part_id: str
    qty: int = Field(ge=1)
    due_at: datetime
    value_inr: float = Field(gt=0)
    customer_alias: str | None = None


class OrderOut(_Out):
    id: str
    factory_id: str
    part_id: str
    qty: int
    due_at: datetime
    value_inr: float
    customer_alias: str | None


class FactoryListOut(_Out):
    items: list[FactoryOut]


class MachineListOut(_Out):
    items: list[MachineOut]


class PartListOut(_Out):
    items: list[PartOut]


class OrderListOut(_Out):
    items: list[OrderOut]
