"""M8 relationship schemas: effective status, guarded transitions, checks, reconfirm."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.enums import BackupStatus, CheckKey, EffectiveStatus


class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")


class CheckOut(_Out):
    key: CheckKey
    done: bool
    done_at: datetime | None


class RelationshipOut(_Out):
    id: str
    owner_id: str
    partner_id: str
    status: BackupStatus
    # default exists only so the ORM row validates before the service overwrites
    # it with the computed value (STALE is read-time, never stored - section 7.5)
    effective_status: EffectiveStatus = EffectiveStatus.POTENTIAL_MATCH
    last_confirmed_at: datetime | None
    customer_approval_required: bool
    notes: str | None
    checks: list[CheckOut] = []


class StatusPatchIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: BackupStatus


class ReconfirmOut(_Out):
    id: str
    last_confirmed_at: datetime