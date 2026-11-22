"""Backup relationships and the guarded check list (section 6).

A status can never be set to READY unless its required checks are done - that
guard lives in core/status_rules.py (Phase 5); this file only stores the state.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import now
from app.db import Base, UTCDateTime
from app.enums import BackupStatus, CheckKey


class BackupRelationship(Base):
    __tablename__ = "backup_relationships"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("factories.id"), index=True)
    partner_id: Mapped[str] = mapped_column(ForeignKey("factories.id"), index=True)
    status: Mapped[BackupStatus] = mapped_column(SAEnum(BackupStatus, native_enum=False), default=BackupStatus.POTENTIAL_MATCH)
    last_confirmed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), default=None)
    customer_approval_required: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(String(500), default=None)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: now())

    checks: Mapped[list["RelationshipCheck"]] = relationship(back_populates="relationship", cascade="all, delete-orphan")


class RelationshipCheck(Base):
    __tablename__ = "relationship_checks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    relationship_id: Mapped[str] = mapped_column(ForeignKey("backup_relationships.id"), index=True)
    key: Mapped[CheckKey] = mapped_column(SAEnum(CheckKey, native_enum=False))
    done: Mapped[bool] = mapped_column(default=False)
    done_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), default=None)

    relationship: Mapped[BackupRelationship] = relationship(back_populates="checks")