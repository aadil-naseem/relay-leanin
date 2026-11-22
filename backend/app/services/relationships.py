"""M8 relationship services: effective status, guarded transitions, checks (section 7.5)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config_loader import load_configs
from app.core import status_rules
from app.core.clock import now
from app.enums import BackupStatus, CheckKey, EffectiveStatus
from app.errors import AppError
from app.models import BackupRelationship, RelationshipCheck


def _staleness_days() -> float:
    return load_configs().readiness.staleness_days


def get_relationship(session: Session, relationship_id: str) -> BackupRelationship:
    relationship = session.get(BackupRelationship, relationship_id)
    if relationship is None:
        raise AppError("NOT_FOUND", f"Relationship {relationship_id!r} does not exist.", status_code=404)
    return relationship


def compute_effective_status(
    relationship: BackupRelationship,
    current: datetime | None = None,
    staleness_days: float | None = None,
) -> EffectiveStatus:
    """EffectiveStatus is computed at read time and never stored (section 7.5)."""
    return status_rules.effective_status(
        relationship.status,
        relationship.last_confirmed_at,
        current or now(),
        staleness_days if staleness_days is not None else _staleness_days(),
    )


def list_relationships_for_owner(session: Session, factory_id: str) -> list[BackupRelationship]:
    return list(
        session.scalars(
            select(BackupRelationship)
            .where(BackupRelationship.owner_id == factory_id)
            .order_by(BackupRelationship.id)
        )
    )


def patch_status(session: Session, relationship_id: str, target: BackupStatus) -> BackupRelationship:
    """Guarded transition: 409 with details.missing_checks when checks are missing."""
    relationship = get_relationship(session, relationship_id)
    done = {check.key for check in relationship.checks if check.done}
    missing = status_rules.missing_checks_for(target, done, relationship.customer_approval_required)
    if missing:
        raise AppError(
            "MISSING_CHECKS",
            f"Cannot move to {target.value}: required checks are not complete.",
            status_code=409,
            details={
                "missing_checks": [key.value for key in missing],
                "target_status": target.value,
            },
        )
    relationship.status = target
    session.commit()
    from app.services import readiness as readiness_service

    readiness_service.record_snapshot(session, relationship.owner_id)
    return relationship


def complete_check(session: Session, relationship_id: str, key: CheckKey) -> BackupRelationship:
    """Mark a check done. CAPACITY_RECONFIRMED refreshes last_confirmed_at (section 7.5)."""
    relationship = get_relationship(session, relationship_id)
    check = next((c for c in relationship.checks if c.key == key), None)
    if check is None:
        # lazily create the row: relationships may not have every check pre-created
        check = RelationshipCheck(id=f"chk_{relationship.id}_{key.value}", relationship_id=relationship.id, key=key)
        relationship.checks.append(check)
    if not check.done:
        check.done = True
        check.done_at = now()
        if key == CheckKey.CAPACITY_RECONFIRMED:
            relationship.last_confirmed_at = now()
            session.commit()
            from app.services import readiness as readiness_service

            readiness_service.record_snapshot(session, relationship.owner_id)
        session.commit()
    return relationship


def reconfirm(session: Session, relationship_id: str) -> BackupRelationship:
    """Refresh last_confirmed_at = now (the staleness cure)."""
    relationship = get_relationship(session, relationship_id)
    relationship.last_confirmed_at = now()
    session.commit()
    from app.services import readiness as readiness_service

    readiness_service.record_snapshot(session, relationship.owner_id)
    return relationship
