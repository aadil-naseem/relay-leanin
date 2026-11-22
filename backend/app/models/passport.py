"""Production Passports, redacted RFQs and explicit sharing consent (section 6).

`passports.data` holds the field -> {value, confidence, source, candidates} map
(section 7.6). A passport is a DRAFT until a human confirms it.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import now
from app.db import Base, UTCDateTime
from app.enums import PassportStatus, ShareLevel


class Passport(Base):
    __tablename__ = "passports"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    part_id: Mapped[str | None] = mapped_column(
        ForeignKey("parts.id", use_alter=True, ondelete="SET NULL"), default=None
    )
    status: Mapped[PassportStatus] = mapped_column(SAEnum(PassportStatus, native_enum=False), default=PassportStatus.DRAFT)
    data: Mapped[dict] = mapped_column(JSON, default=dict)  # field -> {value, confidence, source, candidates}
    extraction_meta: Mapped[dict] = mapped_column(JSON, default=dict)  # provider, latency, source, sha256
    source_sha256: Mapped[str | None] = mapped_column(String(64), default=None)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: now())
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: now(), onupdate=lambda: now())


class Rfq(Base):
    """Redacted RFQ derived from a passport: customer-identifying details removed."""

    __tablename__ = "rfqs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    passport_id: Mapped[str] = mapped_column(ForeignKey("passports.id"), index=True)
    rfq_ref: Mapped[str] = mapped_column(String(64))  # opaque random reference, not the passport id
    content: Mapped[dict] = mapped_column(JSON, default=dict)
    text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: now())


class PassportShare(Base):
    """Explicit consent: a partner may read the RFQ; the FULL passport only with consent."""

    __tablename__ = "passport_shares"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    passport_id: Mapped[str] = mapped_column(ForeignKey("passports.id"), index=True)
    partner_id: Mapped[str] = mapped_column(ForeignKey("factories.id"), index=True)
    level: Mapped[ShareLevel] = mapped_column(SAEnum(ShareLevel, native_enum=False), default=ShareLevel.RFQ)
    consented_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: now())