"""Recovery requests and the simulated tracking stepper (section 6)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import now
from app.db import Base, UTCDateTime


class RecoveryRequest(Base):
    __tablename__ = "recovery_requests"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    factory_id: Mapped[str] = mapped_column(String(64), index=True)
    order_id: Mapped[str] = mapped_column(String(64), index=True)
    stress_test_id: Mapped[str | None] = mapped_column(String(64), default=None)  # set when prefilled from an alert
    passport_id: Mapped[str | None] = mapped_column(String(64), default=None)
    status: Mapped[str] = mapped_column(String(32), default="OPEN")
    selected_partner_id: Mapped[str | None] = mapped_column(String(64), default=None)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: now())

    steps: Mapped[list["RecoveryStep"]] = relationship(
        back_populates="request", cascade="all, delete-orphan"
    )


class RecoveryStep(Base):
    """Simulated stepper: REQUEST_SENT -> ... -> DISPATCH_AND_DELIVERY (M10, mocked)."""

    __tablename__ = "recovery_steps"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    request_id: Mapped[str] = mapped_column(ForeignKey("recovery_requests.id"), index=True)
    step_key: Mapped[str] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(16), default="PENDING")  # PENDING | DONE
    at: Mapped[datetime | None] = mapped_column(UTCDateTime(), default=None)

    request: Mapped[RecoveryRequest] = relationship(back_populates="steps")