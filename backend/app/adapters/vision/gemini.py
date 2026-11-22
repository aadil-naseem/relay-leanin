"""Gemini vision adapter: plain REST via httpx (Phase 12, task 3).

Request shape VERIFIED live in Phase 0 (docs/VERIFIED_FACTS.md):
POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key=...
with contents[].parts[] = [{text}, {inline_data: {mime_type, base64}}] and
generationConfig {responseMimeType: "application/json", temperature: 0}.
Model on this key: gemini-3.5-flash-lite (only responsive model; vision
latency 5.6-13.1 s).

Failure policy: timeout ~30 s; ONE retry on 429/5xx; a quota error starts a
10-minute cooldown during which the provider reports unavailable (fallback 1
of the vision ladder). Any failure returns None - the chain moves on.
"""

from __future__ import annotations

import base64
import json
import logging
import time
from typing import Any

import httpx

from app.settings import get_settings

logger = logging.getLogger(__name__)

BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
TIMEOUT_S = 30.0
RETRY_AFTER_S = 2.0
COOLDOWN_S = 600.0  # 10 minutes after a quota error

_cooldown_until: float = 0.0


def reset_cooldown() -> None:
    """Test helper: clear the quota cooldown."""
    global _cooldown_until
    _cooldown_until = 0.0


def _model() -> str:
    return get_settings().gemini_model


def available() -> bool:
    settings = get_settings()
    if not settings.gemini_api_key or not settings.gemini_model:
        return False
    return time.monotonic() >= _cooldown_until


def extract(image_bytes: bytes, mime_type: str, prompt: str) -> dict[str, Any] | None:
    """One vision call; strict JSON out; None on any failure (never raises)."""
    global _cooldown_until
    settings = get_settings()
    if not available():
        return None

    url = f"{BASE_URL}/{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
    inline = {
        "inline_data": {
            "mime_type": mime_type,
            "data": base64.b64encode(image_bytes).decode("ascii"),
        }
    }
    body = {
        "contents": [{"parts": [{"text": prompt}, inline]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0,
        },
    }

    for attempt in (1, 2):  # one retry on 429/5xx
        try:
            with httpx.Client(timeout=TIMEOUT_S) as client:
                response = client.post(url, json=body)
            if response.status_code in (429, 500, 502, 503, 504):
                if response.status_code == 429:
                    # quota error: 10-minute cooldown, no second attempt
                    _cooldown_until = time.monotonic() + COOLDOWN_S
                    logger.warning("Gemini quota error; vision on cooldown for %s s", COOLDOWN_S)
                    return None
                if attempt == 1:
                    time.sleep(RETRY_AFTER_S)
                    continue
                logger.warning("Gemini %s after retry", response.status_code)
                return None
            if response.status_code != 200:
                logger.warning("Gemini HTTP %s", response.status_code)
                return None
            payload = response.json()
            text = payload["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else None
        except Exception as error:  # noqa: BLE001 - any failure degrades the chain
            logger.warning("Gemini call failed (%s: %s)", type(error).__name__, error)
            return None
    return None
