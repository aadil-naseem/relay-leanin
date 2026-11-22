"""Redacted RFQ builder - deterministic, no AI (section 7.6 step 9).

Allow-list: process route, material + spec, envelope, tightest tolerance,
surface finish, heat treatment / coating, quantity, deadline as "days from
now", inspection requirements, general tolerance standard.

Removed: customer name, drawing / part numbers, revision, title-block fields,
branding, and any free text containing those strings (regex scrub).

Output = JSON + Jinja2 text + a redaction_report. `rfq_ref` is an opaque
random reference, never the passport id.
"""

from __future__ import annotations

import re
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from app.core.clock import now

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
_jinja = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), undefined=StrictUndefined, autoescape=False)

KEEP_KEYS: tuple[str, ...] = (
    "process_route",
    "material",
    "dimensions",
    "tightest_tolerance_mm",
    "general_tolerance_standard",
    "surface_finish_ra_um",
    "heat_treatment",
    "coating",
    "quantity",
    "deadline",
    "inspection_notes",
    "envelope_mm",
)

# identifying strings to scrub from any kept free text
IDENTIFYING_PATTERNS = (
    r"DWG[- ][A-Z]{2,5}-\d{2,4}",  # drawing numbers
    r"\bREV\.?\s*[A-Z0-9]\b",  # revision letters
    r"[A-Z][A-Za-z]+ (Pumps|Hydraulics|Valves|Motors|Engineering|Fasteners|Tools|Components|Works|Steels)(?: \(SAMPLE\))?",
)


def new_rfq_ref() -> str:
    return f"RFQ-{secrets.token_hex(4).upper()}"  # opaque, not derived from the passport id


def _scrub_text(value: str, identifying: list[str]) -> str:
    scrubbed = value
    for needle in identifying:
        if needle:
            scrubbed = scrubbed.replace(needle, "[REDACTED]")
    for pattern in IDENTIFYING_PATTERNS:
        scrubbed = re.sub(pattern, "[REDACTED]", scrubbed)
    return scrubbed


def _collect_identifying(passport: dict[str, Any]) -> list[str]:
    needles: list[str] = []
    for key in ("customer", "part_name", "drawing_no"):
        value = passport.get(key)
        if isinstance(value, str) and value.strip():
            needles.append(value.strip())
    for dimension in passport.get("dimensions") or []:
        label = dimension.get("label") if isinstance(dimension, dict) else None
        if label and "REV" in str(label).upper():
            needles.append(str(label))
    return needles


def build_rfq(
    passport_plain: dict[str, Any],
    current: Any = None,
    *,
    rfq_ref: str | None = None,
) -> tuple[dict[str, Any], str, dict[str, Any]]:
    """(rfq_content, rfq_text, redaction_report) from the plain passport view."""
    identifying = _collect_identifying(passport_plain)
    content: dict[str, Any] = {}
    removed_keys: list[str] = []
    scrubbed_fields: list[str] = []
    kept_keys: list[str] = []

    reference_time = current or now()
    for key in KEEP_KEYS:
        if key not in passport_plain:
            continue
        value = passport_plain.get(key)
        if value is None:
            removed_keys.append(f"{key} (empty)")
            continue

        if key == "deadline":
            deadline = value
            parsed: Any = None
            if isinstance(deadline, datetime):
                parsed = deadline
            elif isinstance(deadline, str):
                try:
                    parsed = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
                except ValueError:
                    parsed = None
            if parsed is not None:
                days = (parsed - reference_time).total_seconds() / 86400.0
                content[key] = {"days_from_now": round(days, 1)}
                kept_keys.append(key)
            else:
                removed_keys.append(f"{key} (unparseable)")
            continue

        if key in ("inspection_notes",) or key == "process_route" and isinstance(value, list) and any(
            isinstance(item, dict) and isinstance(item.get("note"), str) for item in value
        ):
            # free-text lists: scrub identifying strings item by item
            cleaned = []
            changed = False
            for item in value:
                if isinstance(item, str):
                    new = _scrub_text(item, identifying)
                    changed = changed or new != item
                    cleaned.append(new)
                elif isinstance(item, dict):
                    new_item = {
                        k: (_scrub_text(v, identifying) if isinstance(v, str) else v)
                        for k, v in item.items()
                    }
                    if new_item != item:
                        changed = True
                    cleaned.append(new_item)
                else:
                    cleaned.append(item)
            content[key] = cleaned
            kept_keys.append(key)
            if changed:
                scrubbed_fields.append(key)
            continue

        content[key] = value
        kept_keys.append(key)

    for key in passport_plain:
        if key not in KEEP_KEYS and key not in removed_keys:
            removed_keys.append(key)

    report = {
        "removed_keys": sorted(set(removed_keys)),
        "scrubbed_text_fields": sorted(set(scrubbed_fields)),
        "kept_keys": kept_keys,
    }
    rfq_ref = rfq_ref or new_rfq_ref()
    text = _jinja.get_template("rfq.md.j2").render(
        rfq_ref=rfq_ref,
        content=content,
        deadline_days=content.get("deadline", {}).get("days_from_now") if isinstance(content.get("deadline"), dict) else None,
        material=_material_label(content.get("material")),
        route=content.get("process_route") or [],
        quantity=content.get("quantity"),
        envelope=content.get("envelope_mm"),
        tightest=content.get("tightest_tolerance_mm"),
        finish=content.get("surface_finish_ra_um"),
        heat=content.get("heat_treatment"),
        coating=content.get("coating"),
        standard=content.get("general_tolerance_standard"),
        inspections=[item for item in (content.get("inspection_notes") or []) if isinstance(item, str)],
    )
    return content, text, report


def _material_label(material: Any) -> str:
    if isinstance(material, dict):
        grade = material.get("grade") or "unspecified"
        standard = material.get("standard")
        return f"{grade}" + (f" ({standard})" if standard else "")
    return "unspecified"
