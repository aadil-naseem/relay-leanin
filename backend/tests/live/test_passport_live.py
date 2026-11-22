"""Optional live accuracy check (Phase 12, task 9) - marked `live`, opt-in only.

Runs the REAL Gemini provider on the 3 sample PNGs (not the golden cache) and
compares the vision output against expected.json. Writes the accuracy table to
docs/TEST_REPORT.md. Costs 3 free-tier calls; skipped by default.

Usage: .venv/Scripts/python.exe -m pytest tests/live/test_passport_live.py -m live
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pymupdf  # noqa: F401  (ensures the PDF lib is present for parity)
import pytest

from app.adapters.vision import gemini as gemini_provider
from app.settings import get_settings

pytestmark = pytest.mark.live

BACKEND_DIR = Path(__file__).resolve().parents[2]
DRAWINGS_DIR = BACKEND_DIR / "data" / "drawings"
DOCS_DIR = BACKEND_DIR.parent / "docs"
SAMPLES = ("pump_shaft.png", "piston_rod.png", "valve_flange.png")

CHECKED_FIELDS = ("part_name", "drawing_no", "revision", "customer", "quantity", "material")


def _matches(field: str, got, want) -> bool:
    if field == "material":
        return isinstance(got, dict) and str(got.get("grade", "")).upper() == str(want).upper()
    if field == "part_name":
        return str(got).strip().casefold() == str(want).strip().casefold()
    if isinstance(want, (int, float)) and isinstance(got, (int, float)):
        return abs(float(got) - float(want)) < 1e-6
    return str(got).strip().casefold() == str(want).strip().casefold()


def test_live_gemini_accuracy_on_sample_drawings():
    settings = get_settings()
    if not settings.gemini_api_key or not settings.gemini_model:
        pytest.skip("Gemini key not configured")
    expected = json.loads((DRAWINGS_DIR / "expected.json").read_text(encoding="utf-8"))
    prompt = (BACKEND_DIR / "prompts" / "passport_extract.md").read_text(encoding="utf-8")

    rows: list[str] = []
    total_hits = 0
    total_tries = 0
    for name in SAMPLES:
        stem = name.replace(".png", "")
        data = (DRAWINGS_DIR / name).read_bytes()
        started = time.perf_counter()
        fields = gemini_provider.extract(data, "image/png", prompt)
        latency = time.perf_counter() - started
        assert fields is not None, f"{name}: provider returned None"
        hits = 0
        details = []
        for field_name in CHECKED_FIELDS:
            want = expected[stem][field_name]
            got = fields.get(field_name)
            ok = _matches(field_name, got, want)
            hits += ok
            details.append(f"{field_name}: {'OK' if ok else 'MISS'}")
        total_hits += hits
        total_tries += len(CHECKED_FIELDS)
        rows.append(
            f"| {stem} | {hits}/{len(CHECKED_FIELDS)} | {latency:.1f} s | {', '.join(details)} |"
        )

    accuracy = total_hits / total_tries
    lines = [
        "# M2 live accuracy check (Gemini, `live` marker)",
        "",
        f"Run: {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())} - model `{settings.gemini_model}`,",
        "one call per sample PNG, JSON-output mode, temperature 0.",
        "",
        "| Drawing | Fields correct | Latency | Detail |",
        "|---|---|---|---|",
        *rows,
        "",
        f"**Overall accuracy: {accuracy:.0%} ({total_hits}/{total_tries}) on title-block fields.**",
        "",
        "Note: the demo never calls this live path - the golden cache answers for the",
        "sample drawings (sub-3 s). Live vision is the fallback for new drawings.",
        "",
    ]
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "TEST_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    assert accuracy >= 0.8, f"live accuracy {accuracy:.0%} below the 80% target"