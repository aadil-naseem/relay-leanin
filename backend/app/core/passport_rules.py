"""M2 text-rules extractor: regex + catalogue candidates, validators, merge (section 7.6).

Deterministic and explainable - no model involved. The extractor reads the
drawing's text layer and produces candidates per passport field; `merge()`
combines rules and vision candidates into the wrapped field map
(`{value, confidence, source, candidates?}`) exactly per the confidence table:

  rules and vision agree (after normalisation) -> HIGH
  only one source and it passes validation     -> MEDIUM
  only one source and it fails validation      -> LOW (needs review)
  sources disagree                             -> LOW, candidates shown,
                                                  default = rules value
  not found                                    -> MISSING
  edited by the user                           -> CONFIRMED (set by PATCH)

The model's self-reported confidence is never used (section 7.6).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.config_loader import load_configs

CONF_HIGH = "HIGH"
CONF_MEDIUM = "MEDIUM"
CONF_LOW = "LOW"
CONF_MISSING = "MISSING"
CONF_CONFIRMED = "CONFIRMED"

MIN_TOLERANCE_MM = 0.001

PASSPORT_FIELDS: tuple[str, ...] = (
    "part_name",
    "drawing_no",
    "revision",
    "customer",
    "process_route",
    "material",
    "dimensions",
    "tightest_tolerance_mm",
    "general_tolerance_standard",
    "surface_finish_ra_um",
    "heat_treatment",
    "coating",
    "tooling_hints",
    "quantity",
    "deadline",
    "inspection_notes",
    "envelope_mm",
)

REQUIRED_FOR_CONFIRM = ("process_route", "material", "quantity")


@dataclass
class Candidate:
    value: Any
    source: str  # rules | vision
    valid: bool = True
    detail: str = ""


@dataclass
class FieldMerge:
    value: Any
    confidence: str
    source: str | None
    candidates: list[Any] = field(default_factory=list)


# ---------------------------------------------------------------- catalogue


def _catalogue() -> tuple[dict[str, str], dict[str, str]]:
    """(alias -> grade, grade -> family) from materials.yaml."""
    alias_to_grade: dict[str, str] = {}
    grade_family: dict[str, str] = {}
    for material in load_configs().materials:
        grade_family[material.grade] = material.family
        alias_to_grade[material.grade.upper()] = material.grade
        for alias in material.aliases:
            alias_to_grade[str(alias).upper()] = material.grade
    return alias_to_grade, grade_family


def canonical_material(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    alias_map, _ = _catalogue()
    return alias_map.get(value.strip().upper())


def validate_material(value: Any) -> bool:
    if isinstance(value, dict):
        return canonical_material(value.get("grade")) is not None
    return canonical_material(value) is not None


def validate_quantity(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or isinstance(value, str):
        return False
    return float(value).is_integer() and int(value) > 0


def validate_tolerance(value: Any) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    return float(value) >= MIN_TOLERANCE_MM


def validate_positive(value: Any) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    return float(value) > 0


_VALIDATORS = {
    "material": validate_material,
    "quantity": validate_quantity,
    "tightest_tolerance_mm": validate_tolerance,
    "surface_finish_ra_um": validate_positive,
    "envelope_mm": validate_positive,
}


def _validate_field(key: str, value: Any) -> bool:
    validator = _VALIDATORS.get(key)
    if validator is None:
        return True
    if key == "material":
        return validate_material(value)
    return validator(value)


def _normalise(key: str, value: Any) -> Any:
    """Canonical form used to compare rules and vision values."""
    if value is None:
        return None
    if key == "material":
        if isinstance(value, dict):
            grade = canonical_material(value.get("grade"))
            return {"grade": grade} if grade else None
        grade = canonical_material(value)
        return {"grade": grade} if grade else None
    if key == "quantity":
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None
    if key in ("tightest_tolerance_mm", "surface_finish_ra_um", "envelope_mm"):
        try:
            return round(float(value), 4)
        except (TypeError, ValueError):
            return None
    if key == "process_route" and isinstance(value, list):
        return [str(step.get("process", "")).strip().upper() if isinstance(step, dict) else str(step).strip().upper() for step in value]
    if isinstance(value, str):
        return re.sub(r"\s+", " ", value.strip()).casefold()
    if isinstance(value, list):
        return [_normalise(key, item) for item in value]
    return value


# ---------------------------------------------------------------- text extraction


def _material_from_text(text_upper: str) -> dict | None:
    alias_map, grade_family = _catalogue()
    for alias, grade in alias_map.items():
        if re.search(rf"\b{re.escape(alias)}\b", text_upper):
            standard = None
            if re.search(r"\bBS\s*970\b", text_upper):
                standard = "BS 970"
            return {"grade": grade, "standard": standard, "form": None, "family": grade_family.get(grade)}
    return None


def _dimensions_from_text(text: str) -> list[dict]:
    """Labelled bands like `LENGTH 250 ±0.1` or `SHAFT DIAMETER Ø20 h7 +0.02/-0.00`."""
    dimensions: list[dict] = []
    seen: set[tuple] = set()
    for match in re.finditer(
        r"(?P<label>[A-Z][A-Z /]{2,30}?)\s*[Ø⌀]?\s*(?P<nom>\d{1,4}(?:\.\d+)?)\s*(?:mm)?\s*"
        r"(?:[a-z]{1,2}\d{1,2})?\s*"
        r"(?:\+(?P<plus>\d+(?:\.\d+)?)\s*/\s*-(?P<minus>\d+(?:\.\d+)?)|±\s*(?P<sym>\d+(?:\.\d+)?))",
        text,
    ):
        label = match.group("label").strip().title()
        nominal = float(match.group("nom"))
        if match.group("plus") is not None:
            plus, minus = float(match.group("plus")), float(match.group("minus"))
        else:
            plus = minus = float(match.group("sym"))
        # the tolerance value is the max deviation from nominal
        # (+0.02/-0.00 is a 0.02 band; ±0.005 is a 0.005 band)
        band = max(plus, minus)
        if band == 0 or band > 10:
            continue
        key = (label.casefold(), nominal, plus, minus)
        if key in seen:
            continue
        seen.add(key)
        dimensions.append(
            {"label": label, "nominal_mm": nominal, "tol_plus_mm": plus, "tol_minus_mm": minus,
             "critical": band <= 0.05, "band_mm": band}
        )
    return dimensions


def _tolerances_from_text(text: str) -> list[float]:
    """Every tolerance-like number, for the tightest-tolerance derivation."""
    values: list[float] = []
    for match in re.finditer(
        r"(?:±\s*(\d+(?:\.\d+)?)|\+\s*(\d+(?:\.\d+)?)\s*/\s*-\s*(\d+(?:\.\d+)?))",
        text,
    ):
        if match.group(1) is not None:
            values.append(float(match.group(1)))
        else:
            values.extend([float(match.group(2)), float(match.group(3))])
    return [value for value in values if 0 < value <= 1.0]  # tolerance bands, not dimensions


PROCESS_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("TURN", ("TURN", "TURNING", "Ø", "DIAMETER", "LATHE")),
    ("MILL", ("MILL", "KEYWAY", "SLOT", "FACE")),
    ("DRILL_TAP", ("TAP", "TAPPED", "DRILL", "THREADED", "M8", "M6", "M10", "HOLES")),
    ("GRIND_CYL", ("GRIND", "GROUND", "CYLINDRICAL GRIND")),
    ("GRIND_SURF", ("SURFACE GRIND",)),
    ("HEAT_TREAT", ("HARDEN", "HRC", "CASE HARD", "INDUCTION HARDEN", "TEMPER")),
    ("SURFACE_TREAT", ("PLATE", "PLATED", "ANODISE", "ANODIZE", "BLACK OXIDE", "ZINC", "CHROME")),
    ("WIRE_EDM", ("WIRE EDM", "EDM")),
)


def _process_hints(text_upper: str) -> list[str]:
    hints: list[str] = []
    for process, keywords in PROCESS_KEYWORDS:
        if process == "TURN":
            # a diameter symbol alone is too weak (Ø6.8 drill holes) - require a word
            if any(re.search(rf"\b{re.escape(keyword)}\b", text_upper) for keyword in keywords if keyword != "Ø"):
                hints.append(process)
            continue
        if any(re.search(rf"\b{re.escape(keyword)}\b", text_upper) for keyword in keywords):
            hints.append(process)
    # route order: machining before treatment, grinding after its stock process
    order = {code: index for index, code in enumerate(
        ["TURN", "MILL", "DRILL_TAP", "WIRE_EDM", "GRIND_CYL", "GRIND_SURF", "HEAT_TREAT", "SURFACE_TREAT"]
    )}
    return sorted(set(hints), key=lambda code: order.get(code, 99))


def extract_rules(text: str) -> dict[str, Candidate]:
    """Deterministic candidates from the drawing text layer (section 7.6 step 3)."""
    if not text or not text.strip():
        return {}
    upper = text.upper()
    candidates: dict[str, Candidate] = {}

    def put(key: str, value: Any, valid: bool = True, detail: str = "") -> None:
        if value is None or (isinstance(value, (list, dict, str)) and not value) :
            return
        candidates[key] = Candidate(value=value, source="rules", valid=valid, detail=detail)

    # title block labels (search raw text case-insensitively to keep original casing)
    for key, pattern in (
        ("part_name", r"PART:\s*([^\n]+)"),
        ("customer", r"CUSTOMER:\s*([^\n]+)"),
        ("drawing_no", r"DWG\s*NO\.?:\s*([^\n]+)"),
        ("revision", r"REV\.?:\s*([A-Z0-9]+)\b"),
        ("quantity", r"QTY\.?:\s*(\d+)"),
    ):
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            raw = match.group(1).strip()
            if key == "quantity":
                put(key, int(raw), valid=validate_quantity(int(raw)))
            elif key == "part_name":
                put(key, raw.title())
            else:
                put(key, raw)
    if "drawing_no" not in candidates:  # unlabelled but unmistakable pattern
        match = re.search(r"\bDWG-[A-Z]{2,5}-\d{2,4}\b", upper)
        if match:
            put("drawing_no", match.group(0))

    # material (catalogue + aliases)
    material = _material_from_text(upper)
    if material:
        put("material", material, valid=validate_material(material))

    # general tolerance standard
    match = re.search(r"ISO\s*2768\s*[- ]?\s*([A-ZK])\b", upper)
    if match:
        put("general_tolerance_standard", f"ISO 2768-{match.group(1).lower()}")

    # surface finish
    match = re.search(r"RA\s*([0-9]+(?:\.[0-9]+)?)", upper)
    if match:
        value = float(match.group(1))
        put("surface_finish_ra_um", value, valid=validate_positive(value))

    # hardness / heat treatment: copy the exact note line containing HRC
    # heat treatment / coating: copy the exact note line, minus list numbering
    for line in text.splitlines():
        if "HRC" in line.upper():
            put("heat_treatment", re.sub(r"^\s*\d+\.\s*", "", line.strip()).upper())
            break

    # coating: copy the exact note line, minus list numbering
    for line in text.splitlines():
        if re.search(r"HARD CHROME PLATED|BLACK OXIDE|ANODIS[EI]D?|ZINC PLATED", line.upper()):
            put("coating", re.sub(r"^\s*\d+\.\s*", "", line.strip()).upper())
            break

    # dimensions + tolerances
    dimensions = _dimensions_from_text(text)
    if dimensions:
        stored = [
            {k: v for k, v in dim.items() if k != "band_mm"}  # band is a derivation aid, not schema
            for dim in dimensions
        ]
        put("dimensions", stored)
        put("envelope_mm", max(d["nominal_mm"] for d in dimensions), valid=validate_positive(
            max(d["nominal_mm"] for d in dimensions)
        ))
        bands = [d["band_mm"] for d in dimensions] + _tolerances_from_text(text)
        positive = [t for t in bands if 0 < t]
        if positive:
            tightest = min(positive)
            put("tightest_tolerance_mm", tightest, valid=validate_tolerance(tightest))

    # process hints
    hints = _process_hints(upper)
    if hints:
        put("process_route", [{"process": code, "source_hint": True} for code in hints])

    # inspection notes: the numbered notes block, for the RFQ scrub to filter
    notes = [line.strip().title() for line in text.splitlines() if re.match(r"^\s*\d+\.\s+\S", line)]
    if notes:
        put("inspection_notes", notes)

    return candidates


# ---------------------------------------------------------------- merge


def _store_value(key: str, value: Any) -> Any:
    """Canonical storage form for machine-readable fields; raw copy for text."""
    if value is None:
        return None
    normalised = _normalise(key, value)
    if key == "material":
        return normalised  # canonical grade dict
    if key == "quantity":
        return normalised  # int
    if key in ("tightest_tolerance_mm", "surface_finish_ra_um", "envelope_mm"):
        return normalised  # rounded float
    return value


def _candidates_compatible(key: str, rules_value: Any, vision_value: Any) -> bool:
    return _normalise(key, rules_value) == _normalise(key, vision_value)


def merge(rules: dict[str, Candidate], vision: dict[str, Any]) -> tuple[dict[str, FieldMerge], list[str], list[str]]:
    """Combine rule and vision candidates into the wrapped field map (section 7.6 step 5).

    Returns (fields, needs_review, missing_required).
    """
    fields: dict[str, FieldMerge] = {}
    needs_review: list[str] = []
    missing_required: list[str] = []
    tolerance_missing = False

    for key in PASSPORT_FIELDS:
        rule = rules.get(key)
        vision_value = vision.get(key) if isinstance(vision, dict) else None

        if rule is None and vision_value is None:
            fields[key] = FieldMerge(value=None, confidence=CONF_MISSING, source=None)
            if key in REQUIRED_FOR_CONFIRM:
                missing_required.append(key)
            if key == "tightest_tolerance_mm":
                tolerance_missing = True
            continue

        if rule is not None and vision_value is not None:
            if _candidates_compatible(key, rule.value, vision_value):
                fields[key] = FieldMerge(
                    value=_store_value(key, rule.value), confidence=CONF_HIGH, source="rules+vision"
                )
            else:
                needs_review.append(key)
                fields[key] = FieldMerge(
                    value=_store_value(key, rule.value),  # default = rules value (section 7.6)
                    confidence=CONF_LOW,
                    source="rules",
                    candidates=[rule.value, vision_value],
                )
            continue

        lone_value = rule.value if rule is not None else vision_value
        lone_source = "rules" if rule is not None else "vision"
        valid = rule.valid if rule is not None else _validate_field(key, vision_value)
        if valid:
            fields[key] = FieldMerge(
                value=_store_value(key, lone_value), confidence=CONF_MEDIUM, source=lone_source
            )
        else:
            needs_review.append(key)
            fields[key] = FieldMerge(value=_store_value(key, lone_value), confidence=CONF_LOW, source=lone_source)

    # a general tolerance standard also satisfies the tolerance requirement
    if tolerance_missing:
        standard = fields.get("general_tolerance_standard")
        if not (standard and standard.value):
            missing_required.append("tightest_tolerance_mm")
    return fields, needs_review, missing_required


def wrapped_to_plain(fields: dict[str, FieldMerge]) -> dict[str, Any]:
    """The unwrapped passport view (used for the RFQ and confirm guards)."""
    return {key: merge_obj.value for key, merge_obj in fields.items()}
