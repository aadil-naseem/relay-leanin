"""Parts, part steps (the route), and orders (section 6).

part_steps is the dependency spine every other module reads: SPOF (M3) removes
resources from these requirements, the scheduler (M5) walks them in seq order,
matching (M6) checks them against partner machines.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Float, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import now
from app.db import Base, UTCDateTime
from app.enums import ProcessCode


class Part(Base):
    __tablename__ = "parts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    factory_id: Mapped[str] = mapped_column(ForeignKey("factories.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    drawing_no: Mapped[str | None] = mapped_column(String(100), default=None)
    customer_alias: Mapped[str | None] = mapped_column(String(200), default=None)  # never a real customer name
    material: Mapped[str] = mapped_column(String(100))  # canonical grade, validated against materials.yaml
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False)
    typical_batch_qty: Mapped[int] = mapped_column(default=1)
    # use_alter: passports.part_id -> parts.id and parts.passport_id -> passports.id
    # form a cycle; SQLAlchemy creates/drops this one via ALTER (section 6 note).
    passport_id: Mapped[str | None] = mapped_column(
        ForeignKey("passports.id", use_alter=True, ondelete="SET NULL"), default=None
    )

    steps: Mapped[list["PartStep"]] = relationship(back_populates="part", order_by="PartStep.seq")
    orders: Mapped[list["Order"]] = relationship(back_populates="part")


class PartStep(Base):
    __tablename__ = "part_steps"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    part_id: Mapped[str] = mapped_column(ForeignKey("parts.id"), index=True)
    seq: Mapped[int]  # 1-based route order
    process: Mapped[ProcessCode] = mapped_column(SAEnum(ProcessCode, native_enum=False))
    hours_per_unit: Mapped[float] = mapped_column(Float, default=0.0)  # planner estimate, editable
    setup_hours: Mapped[float] = mapped_column(Float, default=0.0)
    tolerance_mm: Mapped[float | None] = mapped_column(Float, default=None)  # tightest tolerance this step must hold
    outsourced: Mapped[bool] = mapped_column(Boolean, default=False)

    part: Mapped[Part] = relationship(back_populates="steps")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    factory_id: Mapped[str] = mapped_column(ForeignKey("factories.id"), index=True)
    part_id: Mapped[str] = mapped_column(ForeignKey("parts.id"), index=True)
    qty: Mapped[int]
    due_at: Mapped[datetime] = mapped_column(UTCDateTime())
    value_inr: Mapped[float]
    customer_alias: Mapped[str | None] = mapped_column(String(200), default=None)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: now())

    part: Mapped[Part] = relationship(back_populates="orders")