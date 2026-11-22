"""Factory aggregate: factories, machines, vendors/suppliers, vendor links (section 6).

Machines are individual rows: "3 lathes" creates 3 rows, so two lathes are never
an SPOF (section 7.1). Vendors carry one process; suppliers carry one material.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, ForeignKey, String, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import now
from app.db import Base, UTCDateTime
from app.enums import ProcessCode, Role, VendorKind


class Factory(Base):
    __tablename__ = "factories"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    role: Mapped[Role] = mapped_column(SAEnum(Role, native_enum=False))
    name: Mapped[str] = mapped_column(String(200))
    is_sample: Mapped[bool] = mapped_column(default=True)  # R9: demo data is labelled
    lat: Mapped[float]
    lon: Mapped[float]
    cluster_id: Mapped[str] = mapped_column(String(64))
    hazard_zone_id: Mapped[str | None] = mapped_column(String(64), default=None)
    grid_id: Mapped[str | None] = mapped_column(String(64), default=None)
    shift_hours_per_day: Mapped[float] = mapped_column(default=16.0)
    materials_handled: Mapped[list] = mapped_column(JSON, default=list)
    typical_lead_time_hours: Mapped[float | None] = mapped_column(default=None)
    mobilisation_hours: Mapped[float | None] = mapped_column(default=None)  # partners
    spare_hours_per_week: Mapped[dict] = mapped_column(JSON, default=dict)  # process -> hours (partners)
    contacts: Mapped[list] = mapped_column(JSON, default=list)  # contact roles
    created_at: Mapped[Any] = mapped_column(UTCDateTime(), default=lambda: now())

    machines: Mapped[list["Machine"]] = relationship(back_populates="factory")
    vendor_links: Mapped[list["VendorLink"]] = relationship(back_populates="factory")


class Machine(Base):
    __tablename__ = "machines"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    factory_id: Mapped[str] = mapped_column(ForeignKey("factories.id"), index=True)
    process: Mapped[ProcessCode] = mapped_column(SAEnum(ProcessCode, native_enum=False))
    name: Mapped[str] = mapped_column(String(200))
    achievable_tolerance_mm: Mapped[float | None] = mapped_column(default=None)
    envelope_mm: Mapped[float | None] = mapped_column(default=None)  # largest dimension the machine accepts
    available: Mapped[bool] = mapped_column(default=True)

    factory: Mapped[Factory] = relationship(back_populates="machines")


class Vendor(Base):
    """VENDOR performs a process (e.g. heat treatment); SUPPLIER provides a material."""

    __tablename__ = "vendors"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    kind: Mapped[VendorKind] = mapped_column(SAEnum(VendorKind, native_enum=False))
    name: Mapped[str] = mapped_column(String(200))
    is_sample: Mapped[bool] = mapped_column(default=True)
    lat: Mapped[float]
    lon: Mapped[float]
    cluster_id: Mapped[str] = mapped_column(String(64))
    hazard_zone_id: Mapped[str | None] = mapped_column(String(64), default=None)
    grid_id: Mapped[str | None] = mapped_column(String(64), default=None)
    process: Mapped[ProcessCode | None] = mapped_column(SAEnum(ProcessCode, native_enum=False), default=None)
    material: Mapped[str | None] = mapped_column(String(100), default=None)  # material grade for suppliers
    turnaround_hours: Mapped[float] = mapped_column(default=24.0)
    created_at: Mapped[Any] = mapped_column(UTCDateTime(), default=lambda: now())


class VendorLink(Base):
    """An approved vendor/supplier of a factory."""

    __tablename__ = "vendor_links"
    __table_args__ = (UniqueConstraint("factory_id", "vendor_id", name="uq_vendor_link"),)

    factory_id: Mapped[str] = mapped_column(ForeignKey("factories.id"), primary_key=True)
    vendor_id: Mapped[str] = mapped_column(ForeignKey("vendors.id"), primary_key=True)

    factory: Mapped[Factory] = relationship(back_populates="vendor_links")
    vendor: Mapped[Vendor] = relationship()