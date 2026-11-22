"""Phase 12: rules-only extraction accuracy + the merge confidence table (section 7.6)."""

from __future__ import annotations

import json
from pathlib import Path

import pymupdf
import pytest

from app.core import passport_rules as rules

BACKEND_DIR = Path(__file__).resolve().parents[2]
DRAWINGS_DIR = BACKEND_DIR / "data" / "drawings"

SAMPLES = ("pump_shaft", "piston_rod", "valve_flange")

# fields the accuracy check counts as critical (target >= 80% overall)
CRITICAL_FIELDS = (
    "part_name",
    "drawing_no",
    "revision",
    "customer",
    "quantity",
    "material",
    "general_tolerance_standard",
    "surface_finish_ra_um",
    "tightest_tolerance_mm",
    "process_route",
)


def _text(stem: str) -> str:
    doc = pymupdf.open(str(DRAWINGS_DIR / f"{stem}.pdf"))
    try:
        return doc[0].get_text()
    finally:
        doc.close()


@pytest.fixture(scope="module")
def expected():
    return json.loads((DRAWINGS_DIR / "expected.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def extracted():
    return {stem: rules.extract_rules(_text(stem)) for stem in SAMPLES}


# ---------------------------------------------------------------- accuracy


def _field_matches(key: str, candidate, truth) -> bool:
    if key == "material":
        return isinstance(candidate, dict) and candidate.get("grade") == truth
    if key == "process_route":
        got = [step["process"] for step in (candidate or [])]
        return sorted(got) == sorted(truth)
    if key in ("part_name",):
        return str(candidate).casefold() == str(truth).casefold()
    if isinstance(truth, float):
        return candidate is not None and abs(float(candidate) - truth) < 1e-6
    if truth is None:
        return candidate is None  # correctly NOT found (e.g. no standard on piston)
    return candidate == truth


def test_rules_only_accuracy_at_least_80_percent(expected, extracted):
    """Section 10 Phase 12 test 8: rules-only >= 80% of critical fields."""
    hits = 0
    tries = 0
    misses: list[str] = []
    for stem in SAMPLES:
        truth = expected[stem]
        candidates = extracted[stem]
        for key in CRITICAL_FIELDS:
            if key not in truth or truth[key] is None and key != "general_tolerance_standard":
                continue
            tries += 1
            candidate = candidates.get(key)
            value = candidate.value if candidate else None
            if _field_matches(key, value, truth[key]):
                hits += 1
            else:
                misses.append(f"{stem}.{key}: got {value!r}, want {truth[key]!r}")
    ratio = hits / tries
    assert ratio >= 0.8, f"accuracy {ratio:.0%} ({hits}/{tries}) - misses: {misses}"


def test_every_drawing_finds_the_core_fields(extracted):
    for stem in SAMPLES:
        candidates = extracted[stem]
        for key in ("part_name", "drawing_no", "revision", "customer", "quantity", "material"):
            assert key in candidates, f"{stem}.{key} missing"
            assert candidates[key].valid, f"{stem}.{key} invalid"


def test_tolerances_per_drawing(extracted):
    assert extracted["pump_shaft"]["tightest_tolerance_mm"].value == pytest.approx(0.02)
    assert extracted["piston_rod"]["tightest_tolerance_mm"].value == pytest.approx(0.005)
    assert extracted["valve_flange"]["tightest_tolerance_mm"].value == pytest.approx(0.05)


def test_process_hints_match_expected_routes(expected, extracted):
    for stem in SAMPLES:
        route = [step["process"] for step in extracted[stem]["process_route"].value]
        assert sorted(route) == sorted(expected[stem]["process_hints"]), stem


def test_customer_keeps_authored_casing(extracted):
    assert extracted["pump_shaft"]["customer"].value == "ACME Pumps (SAMPLE)"
    assert extracted["valve_flange"]["customer"].value == "Delta Valves (SAMPLE)"


def test_heat_treatment_and_coating_copied_exactly(extracted):
    assert extracted["piston_rod"]["heat_treatment"].value == "INDUCTION HARDENED HRC 58-62"
    assert extracted["piston_rod"]["coating"].value == "HARD CHROME PLATED 0.02 THICK"
    assert "heat_treatment" not in extracted["pump_shaft"]
    assert "coating" not in extracted["pump_shaft"]


def test_dimensions_have_schema_shape(extracted):
    for dim in extracted["pump_shaft"]["dimensions"].value:
        assert set(dim) == {"label", "nominal_mm", "tol_plus_mm", "tol_minus_mm", "critical"}


# ---------------------------------------------------------------- validators


def test_validators():
    assert rules.validate_material({"grade": "EN8"}) is True
    assert rules.validate_material({"grade": "UNOBTAINIUM"}) is False
    assert rules.validate_quantity(200) is True
    assert rules.validate_quantity(0) is False
    assert rules.validate_quantity(12.5) is False
    assert rules.validate_quantity("200") is False
    assert rules.validate_tolerance(0.005) is True
    assert rules.validate_tolerance(0.0) is False  # 0 is not a tolerance
    assert rules.validate_tolerance(0.0001) is False  # below the 0.001 mm floor
    assert rules.validate_positive(1.6) is True
    assert rules.validate_positive(-1) is False


def test_material_normalisation_via_aliases():
    assert rules.canonical_material("EN-8") == "EN8"
    assert rules.canonical_material("817M40") == "EN24"
    assert rules.canonical_material("AISI304") == "SS304"
    assert rules.canonical_material("6061-T6") == "Al6061"
    assert rules.canonical_material("unknown") is None


# ---------------------------------------------------------------- merge table


def _rule(value, valid=True):
    return rules.Candidate(value=value, source="rules", valid=valid)


def test_merge_agree_is_high():
    fields, review, missing = rules.merge({"quantity": _rule(200)}, {"quantity": 200})
    assert fields["quantity"].confidence == "HIGH"
    assert fields["quantity"].source == "rules+vision"
    assert review == []


def test_merge_agrees_after_normalisation():
    # EN-8 (rules) vs en8 (vision) -> same canonical grade
    fields, _review, _missing = rules.merge({"material": _rule({"grade": "EN-8"})}, {"material": {"grade": "en8"}})
    assert fields["material"].confidence == "HIGH"
    assert fields["material"].value == {"grade": "EN8"}


def test_merge_single_valid_source_is_medium():
    fields, review, _missing = rules.merge({}, {"surface_finish_ra_um": 1.6})
    assert fields["surface_finish_ra_um"].confidence == "MEDIUM"
    assert fields["surface_finish_ra_um"].source == "vision"
    assert review == []


def test_merge_single_invalid_source_is_low_and_flagged():
    fields, review, _missing = rules.merge({}, {"tightest_tolerance_mm": 0.0})
    assert fields["tightest_tolerance_mm"].confidence == "LOW"
    assert "tightest_tolerance_mm" in review


def test_merge_disagreement_defaults_to_rules_with_candidates():
    fields, review, _missing = rules.merge(
        {"tightest_tolerance_mm": _rule(0.02)}, {"tightest_tolerance_mm": 0.0}
    )
    entry = fields["tightest_tolerance_mm"]
    assert entry.confidence == "LOW"
    assert entry.value == 0.02  # rules value is the default (section 7.6)
    assert entry.candidates == [0.02, 0.0]
    assert "tightest_tolerance_mm" in review


def test_merge_missing_fields_flagged():
    fields, review, missing = rules.merge({}, {})
    for key in rules.PASSPORT_FIELDS:
        assert fields[key].confidence == "MISSING"
    assert set(missing) == {"process_route", "material", "quantity", "tightest_tolerance_mm"}
    assert review == []


def test_merge_general_standard_satisfies_tolerance_requirement():
    _fields, _review, missing = rules.merge(
        {"general_tolerance_standard": _rule("ISO 2768-m")}, {}
    )
    assert "tightest_tolerance_mm" not in missing


def test_merge_never_uses_model_confidence():
    """A vision 'confidence' key must be ignored - ours comes from agreement only."""
    fields, _review, _missing = rules.merge({}, {"quantity": 200, "confidence": "SUPER"})
    assert fields["quantity"].confidence == "MEDIUM"


def test_empty_text_gives_empty_draft():
    assert rules.extract_rules("") == {}
    assert rules.extract_rules("   \n  ") == {}