"""Golden result cache: instant extraction by file SHA-256 (section 7.6 step 1).

A successful provider result is stored under `data/golden/<sha>.json`, so the
demo never depends on the network: the same file returns the stored result
immediately, marked `source: cache`. Files here are committed (Phase 4 rule:
everything the runtime needs is prefetched once).

Tests write to `FCD_GOLDEN_WRITE_DIR` (a temp dir) so they can never pollute
the committed cache; reads check the test dir first, then the committed one.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[3]  # adapters/vision/cache.py -> backend
GOLDEN_DIR = BACKEND_DIR / "data" / "golden"


def _write_dir() -> Path:
    override = os.environ.get("FCD_GOLDEN_WRITE_DIR")
    return Path(override) if override else GOLDEN_DIR


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_candidates(sha256: str) -> list[Path]:
    paths = [_write_dir() / f"{sha256}.json"]
    committed = GOLDEN_DIR / f"{sha256}.json"
    if committed not in paths:
        paths.append(committed)
    return paths


def golden_path(sha256: str) -> Path:
    return _write_dir() / f"{sha256}.json"


def load_golden(sha256: str) -> dict[str, Any] | None:
    for path in _read_candidates(sha256):
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        fields = payload.get("fields")
        if isinstance(fields, dict):
            return fields
    return None


def save_golden(sha256: str, fields: dict[str, Any], provider: str, model: str | None = None) -> Path:
    out_dir = _write_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "sha256": sha256,
        "provider": provider,
        "model": model,
        "fields": fields,
        "saved_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    path = out_dir / f"{sha256}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
