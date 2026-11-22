"""Backup relationship status state machine + guards (section 7.5).

Pure logic: no database access, no FastAPI imports. The service layer turns a
violated guard into HTTP 409 with details.missing_checks; STALE is computed at
read time and never stored (R9 note in enums).
"""

from __future__ import annotations

from datetime import datetime, timedelta

from app.enums import BackupStatus, CheckKey, EffectiveStatus

ALL_CHECKS = frozenset(CheckKey)


def required_checks_for(status: BackupStatus, customer_approval_required: bool) -> set[CheckKey]:
    """Checks that must be done before `status` is a legal state."""
    if status == BackupStatus.APPROVAL_PENDING:
        return {CheckKey.TECH_ASSESSMENT_DONE}
    if status == BackupStatus.READY:
        required = {
            CheckKey.TECH_ASSESSMENT_DONE,
            CheckKey.SAMPLE_APPROVED,
            CheckKey.TERMS_AGREED,
            CheckKey.CAPACITY_RECONFIRMED,
        }
        if customer_approval_required:
            required.add(CheckKey.CUSTOMER_APPROVED)
        return required
    return set()  # POTENTIAL_MATCH, ASSESSMENT_IN_PROGRESS, UNAVAILABLE_EXPIRED


def missing_checks_for(
    status: BackupStatus,
    checks_done: set[CheckKey],
    customer_approval_required: bool,
) -> list[CheckKey]:
    required = required_checks_for(status, customer_approval_required)
    return sorted(required - checks_done, key=lambda key: key.value)


def effective_status(
    status: BackupStatus,
    last_confirmed_at: datetime | None,
    now_utc: datetime,
    staleness_days: float,
) -> EffectiveStatus:
    """READY past the staleness window reads as STALE and does not count (section 7.5)."""
    if status == BackupStatus.READY and last_confirmed_at is not None:
        if (now_utc - last_confirmed_at) > timedelta(days=staleness_days):
            return EffectiveStatus.STALE
    return EffectiveStatus(status.value)


def is_expiring_soon(
    status: BackupStatus,
    last_confirmed_at: datetime | None,
    now_utc: datetime,
    staleness_days: float,
    expiring_soon_days: float,
) -> bool:
    """READY and inside `expiring_soon_days` of going stale (preparedness review)."""
    if status != BackupStatus.READY or last_confirmed_at is None:
        return False
    age = now_utc - last_confirmed_at
    return timedelta(days=staleness_days - expiring_soon_days) <= age <= timedelta(days=staleness_days)
