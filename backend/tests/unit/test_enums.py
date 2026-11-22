"""Phase 2: enum coverage exactly as blueprint section 6 defines it."""

from app.enums import (
    BackupStatus,
    CheckKey,
    Confidence,
    EffectiveStatus,
    FallbackLevel,
    HazardType,
    OrderState,
    PassportStatus,
    ProcessCode,
    RiskLevel,
    Role,
    ShareLevel,
    Trigger,
    VendorKind,
    WeatherMode,
)


def test_role():
    assert [m.value for m in Role] == ["OWNER", "PARTNER"]


def test_process_code():
    assert [m.value for m in ProcessCode] == [
        "TURN", "MILL", "DRILL_TAP", "GRIND_CYL", "GRIND_SURF", "WIRE_EDM", "HEAT_TREAT", "SURFACE_TREAT",
    ]


def test_backup_status():
    assert [m.value for m in BackupStatus] == [
        "POTENTIAL_MATCH", "ASSESSMENT_IN_PROGRESS", "APPROVAL_PENDING", "READY", "UNAVAILABLE_EXPIRED",
    ]


def test_effective_status_adds_stale_only():
    values = {m.value for m in EffectiveStatus}
    assert values == {m.value for m in BackupStatus} | {"STALE"}


def test_check_key():
    assert [m.value for m in CheckKey] == [
        "TECH_ASSESSMENT_DONE", "SAMPLE_APPROVED", "TERMS_AGREED", "CAPACITY_RECONFIRMED", "CUSTOMER_APPROVED",
    ]


def test_hazard_type():
    assert [m.value for m in HazardType] == ["FLOOD", "POWER_OUTAGE", "WATER_OUTAGE", "ACCESS_BLOCKED", "RESOURCE_DOWN"]


def test_risk_level_bands():
    assert RiskLevel.from_score(0).value == "LOW"
    assert RiskLevel.from_score(24.9).value == "LOW"
    assert RiskLevel.from_score(25).value == "MODERATE"
    assert RiskLevel.from_score(49.9).value == "MODERATE"
    assert RiskLevel.from_score(50).value == "HIGH"
    assert RiskLevel.from_score(74.9).value == "HIGH"
    assert RiskLevel.from_score(75).value == "SEVERE"
    assert RiskLevel.from_score(100).value == "SEVERE"


def test_order_state():
    assert [m.value for m in OrderState] == ["ON_TRACK", "AT_RISK", "LATE"]


def test_fallback_level():
    assert [m.value for m in FallbackLevel] == ["READY", "POTENTIAL_ONLY", "NONE"]


def test_confidence():
    assert [m.value for m in Confidence] == ["HIGH", "MEDIUM", "LOW", "MISSING", "CONFIRMED"]


def test_weather_mode_is_lowercase():
    assert [m.value for m in WeatherMode] == ["live", "replay", "synthetic"]


def test_small_enums():
    assert [m.value for m in Trigger] == ["AUTO", "MANUAL"]
    assert [m.value for m in VendorKind] == ["VENDOR", "SUPPLIER"]
    assert [m.value for m in PassportStatus] == ["DRAFT", "CONFIRMED"]
    assert [m.value for m in ShareLevel] == ["RFQ", "FULL"]