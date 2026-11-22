"""Calculation log builder (section 3.6).

Every service returns `trace: [{step, detail, inputs, output}]` - plain
arithmetic evidence, e.g. "rolling 24 h rain 148 mm -> hazard 0.86". The UI
renders it in a collapsible "How was this calculated?" panel. Entries are
JSON-safe: anything that cannot serialise is stringified rather than dropped.
"""

from __future__ import annotations

import json
from typing import Any


def _safe(value: Any) -> Any:
    """Recursively make a value JSON-safe; anything unserialisable becomes a string."""
    if isinstance(value, dict):
        return {str(key): _safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe(item) for item in value]
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return str(value)


class TraceBuilder:
    """Accumulates ordered, JSON-safe trace entries."""

    def __init__(self) -> None:
        self._entries: list[dict[str, Any]] = []

    def add(self, step: str, detail: str, inputs: Any = None, output: Any = None) -> dict[str, Any]:
        entry = {"step": step, "detail": detail, "inputs": _safe(inputs), "output": _safe(output)}
        self._entries.append(entry)
        return entry

    def to_list(self) -> list[dict[str, Any]]:
        return list(self._entries)

    def __len__(self) -> int:
        return len(self._entries)