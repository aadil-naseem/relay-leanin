"""Vision provider interface (section 7.6, Phase 12 task 3).

A provider turns drawing bytes into a plain JSON dict of passport fields
(the unwrapped schema), or returns None when it cannot read the drawing.
Providers never raise into the pipeline - the chain treats any exception as
"provider unavailable" and moves on (section 3.4).
"""

from __future__ import annotations

from typing import Any, Protocol


class VisionProvider(Protocol):
    name: str

    def available(self) -> bool:
        """False when the provider cannot possibly work (no key, no model, ...)."""
        ...

    def extract(self, image_bytes: bytes, mime_type: str) -> dict[str, Any] | None:
        """Plain passport fields dict, or None on any failure."""
        ...
