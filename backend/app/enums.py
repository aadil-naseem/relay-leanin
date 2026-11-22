"""Canonical enums (blueprint section 6). Stored as string names in SQLite.

EffectiveStatus is computed at read time and never stored. RiskLevel.from_score
carries the score bands: LOW < 25, MODERATE 25-49, HIGH 50-74, SEVERE >= 75.
"""

from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    OWNER = "OWNER"
    PARTNER = "PARTNER"


class ProcessCode(str, Enum):
    TURN = "TURN"
    MILL = "MILL"
    DRILL_TAP = "DRILL_TAP"
    GRIND_CYL = "GRIND_CYL"
    GRIND_SURF = "GRIND_SURF"
    WIRE_EDM = "WIRE_EDM"
    HEAT_TREAT = "HEAT_TREAT"
    SURFACE_TREAT = "SURFACE_TREAT"


class BackupStatus(str, Enum):
    POTENTIAL_MATCH = "POTENTIAL_MATCH"
    ASSESSMENT_IN_PROGRESS = "ASSESSMENT_IN_PROGRESS"
    APPROVAL_PENDING = "APPROVAL_PENDING"
    READY = "READY"
    UNAVAILABLE_EXPIRED = "UNAVAILABLE_EXPIRED"


class EffectiveStatus(str, Enum):
    """BackupStatus + STALE. STALE = READY but last confirmed beyond the staleness
    window; computed at read time, never stored (R9: it does not count in the score)."""

    POTENTIAL_MATCH = "POTENTIAL_MATCH"
    ASSESSMENT_IN_PROGRESS = "ASSESSMENT_IN_PROGRESS"
    APPROVAL_PENDING = "APPROVAL_PENDING"
    READY = "READY"
    STALE = "STALE"
    UNAVAILABLE_EXPIRED = "UNAVAILABLE_EXPIRED"


class CheckKey(str, Enum):
    TECH_ASSESSMENT_DONE = "TECH_ASSESSMENT_DONE"
    SAMPLE_APPROVED = "SAMPLE_APPROVED"
    TERMS_AGREED = "TERMS_AGREED"
    CAPACITY_RECONFIRMED = "CAPACITY_RECONFIRMED"
    CUSTOMER_APPROVED = "CUSTOMER_APPROVED"


class HazardType(str, Enum):
    FLOOD = "FLOOD"
    POWER_OUTAGE = "POWER_OUTAGE"
    WATER_OUTAGE = "WATER_OUTAGE"
    ACCESS_BLOCKED = "ACCESS_BLOCKED"
    RESOURCE_DOWN = "RESOURCE_DOWN"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    SEVERE = "SEVERE"

    @classmethod
    def from_score(cls, score: float) -> "RiskLevel":
        if score < 25:
            return cls.LOW
        if score < 50:
            return cls.MODERATE
        if score < 75:
            return cls.HIGH
        return cls.SEVERE


class OrderState(str, Enum):
    ON_TRACK = "ON_TRACK"
    AT_RISK = "AT_RISK"
    LATE = "LATE"


class FallbackLevel(str, Enum):
    READY = "READY"
    POTENTIAL_ONLY = "POTENTIAL_ONLY"
    NONE = "NONE"


class Confidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    MISSING = "MISSING"
    CONFIRMED = "CONFIRMED"


class WeatherMode(str, Enum):
    LIVE = "live"
    REPLAY = "replay"
    SYNTHETIC = "synthetic"


class Trigger(str, Enum):
    AUTO = "AUTO"
    MANUAL = "MANUAL"


class VendorKind(str, Enum):
    VENDOR = "VENDOR"
    SUPPLIER = "SUPPLIER"


class PassportStatus(str, Enum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"


class ShareLevel(str, Enum):
    RFQ = "RFQ"
    FULL = "FULL"