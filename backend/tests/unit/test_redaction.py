"""Phase 12: redacted RFQ builder - allow-list, scrub, opaque ref (section 7.6 step 9)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.core import redaction


def _passport() -> dict:
    return {
        "part_name": "Pump Shaft",
        "drawing_no": "DWG-PSH-014",
        "revision": "B",
        "customer": "ACME Pumps (SAMPLE)",
        "process_route": [{"process": "TURN"}, {"process": "MILL"}],
        "material": {"grade": "EN8", "standard": "BS 970", "form": None},
        "dimensions": [{"label": "Shaft Diameter", "nominal_mm": 20.0, "tol_plus_mm": 0.02, "tol_minus_mm": 0.0, "critical": True}],
        "tightest_tolerance_mm": 0.02,
        "general_tolerance_standard": "ISO 2768-m",
        "surface_finish_ra_um": 1.6,
        "heat_treatment": None,
        "coating": "HARD CHROME PLATED 0.02 THICK",
        "tooling_hints": ["INTERNAL - DO NOT SHARE"],
        "quantity": 200,
        "deadline": datetime(2026, 11, 16, 9, 0, tzinfo=timezone.utc),
        "inspection_notes": ["First-article inspection for ACME Pumps (SAMPLE)", "Deburr all edges"],
        "envelope_mm": 250.0,
    }


def test_allow_list_keeps_technical_content_only():
    content, text, report = redaction.build_rfq(_passport(), current=datetime(2026, 11, 14, 9, 0, tzinfo=timezone.utc))
    kept = set(report["kept_keys"])
    assert {"process_route", "material", "dimensions", "tightest_tolerance_mm", "quantity", "envelope_mm",
            "general_tolerance_standard", "surface_finish_ra_um", "coating", "inspection_notes", "deadline"} <= kept
    # identifying fields are gone
    for key in ("part_name", "drawing_no", "revision", "customer", "tooling_hints"):
        assert key not in content and key in " ".join(report["removed_keys"]), key


def test_deadline_becomes_days_from_now():
    content, _text, _report = redaction.build_rfq(_passport(), current=datetime(2026, 11, 14, 9, 0, tzinfo=timezone.utc))
    assert content["deadline"] == {"days_from_now": pytest.approx(2.0, abs=0.01)}


def test_deadline_accepts_iso_strings():
    passport = _passport()
    passport["deadline"] = "2026-11-16T09:00:00Z"
    content, _text, report = redaction.build_rfq(passport, current=datetime(2026, 11, 14, 9, 0, tzinfo=timezone.utc))
    assert content["deadline"]["days_from_now"] == pytest.approx(2.0, abs=0.01)
    assert "deadline (unparseable)" not in " ".join(report["removed_keys"])


def test_scrub_removes_identifying_strings_from_free_text():
    content, _text, report = redaction.build_rfq(_passport(), current=datetime(2026, 11, 14, 9, 0, tzinfo=timezone.utc))
    notes = content["inspection_notes"]
    assert any("[REDACTED]" in item for item in notes)
    assert not any("ACME" in item for item in notes)
    assert "inspection_notes" in report["scrubbed_text_fields"]


def test_leak_test_holds_for_json_and_text():
    content, text, _report = redaction.build_rfq(_passport(), current=datetime(2026, 11, 14, 9, 0, tzinfo=timezone.utc))
    flat = str(content) + text
    for needle in ("Pump Shaft", "DWG-PSH-014", "ACME", "PSH"):
        assert needle not in flat, needle


def test_report_reference_matches_printable_rfq_reference():
    reference = "RFQ-PHASE14"
    content, text, report = redaction.build_rfq(
        _passport(),
        current=datetime(2026, 11, 14, 9, 0, tzinfo=timezone.utc),
        rfq_ref=reference,
    )
    assert reference in text
    assert "rfq_ref" not in content  # the opaque reference is not a technical field
    assert "rfq_ref" not in report


def test_rfq_ref_is_opaque_and_random():
    ref_a = redaction.new_rfq_ref()
    ref_b = redaction.new_rfq_ref()
    assert ref_a.startswith("RFQ-") and ref_b.startswith("RFQ-")
    assert ref_a != ref_b
    assert "PSH" not in ref_a  # not derived from the drawing number


def test_empty_passport_gives_minimal_rfq():
    content, text, report = redaction.build_rfq({}, current=datetime(2026, 11, 14, 9, 0, tzinfo=timezone.utc))
    assert content == {}
    assert report["kept_keys"] == []
    assert "RECOVERY RFQ" in text


def test_missing_material_shows_unspecified():
    passport = _passport()
    passport["material"] = None
    _content, text, _report = redaction.build_rfq(passport)
    assert "unspecified" in text
