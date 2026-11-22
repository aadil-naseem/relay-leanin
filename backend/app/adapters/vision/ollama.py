"""Ollama vision adapter - OPTIONAL and disabled in this deployment (deviation D3).

A local vision model would consume most of the remaining E: space, so the
provider is intentionally absent from the chain. The adapter exists so the
chain order in settings stays forward-compatible: it reports unavailable and
returns None, which the pipeline already treats as "provider not usable".
"""

from __future__ import annotations

from typing import Any


def available() -> bool:
    return False  # dropped for space (docs/PROGRESS.md D3)


def extract(_image_bytes: bytes, _mime_type: str, _prompt: str) -> dict[str, Any] | None:
    return None
