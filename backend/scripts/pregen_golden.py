"""Pre-generate golden vision results for the 3 sample drawings (Phase 12, task 5).

One Gemini call per PNG (5-13 s each on this key), stored under
data/golden/<sha>.json and committed, so the demo never depends on the
network. Safe to re-run: identical files hit the cache and skip the call.

This script touches the real provider - run it deliberately, not in tests.

Usage: python scripts/pregen_golden.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.adapters.vision import cache as golden_cache  # noqa: E402
from app.adapters.vision import gemini as gemini_provider  # noqa: E402
from app.settings import get_settings  # noqa: E402

DRAWINGS_DIR = BACKEND_DIR / "data" / "drawings"
SAMPLES = ("pump_shaft.png", "piston_rod.png", "valve_flange.png")


def main() -> int:
    settings = get_settings()
    if not settings.gemini_api_key or not settings.gemini_model:
        print("ERROR: GEMINI_API_KEY / GEMINI_MODEL not configured")
        return 1
    prompt = (BACKEND_DIR / "prompts" / "passport_extract.md").read_text(encoding="utf-8")

    for name in SAMPLES:
        path = DRAWINGS_DIR / name
        data = path.read_bytes()
        sha = golden_cache.sha256_of(data)
        if golden_cache.load_golden(sha) is not None:
            print(f"{name}: golden already present ({sha[:12]}...) - skipped")
            continue
        if not gemini_provider.available():
            print("ERROR: gemini provider unavailable (key/cooldown)")
            return 1
        started = time.perf_counter()
        fields = gemini_provider.extract(data, "image/png", prompt)
        latency = time.perf_counter() - started
        if fields is None:
            print(f"{name}: FAILED ({latency:.1f}s)")
            return 1
        out = golden_cache.save_golden(sha, fields, "gemini", settings.gemini_model)
        non_null = sum(1 for v in fields.values() if v is not None)
        print(f"{name}: OK in {latency:.1f}s -> {out.name} ({non_null}/{len(fields)} fields non-null)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
