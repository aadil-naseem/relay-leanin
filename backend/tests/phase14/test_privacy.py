"""Phase 14 privacy checks: provider credentials never appear in logs."""

from __future__ import annotations

import httpx
import respx

from app.adapters.vision import gemini
from app.settings import get_settings

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent"


def test_gemini_secret_is_not_logged_on_provider_failure(monkeypatch, caplog):
    secret = "phase14-test-secret-never-log"
    monkeypatch.setenv("GEMINI_API_KEY", secret)
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    get_settings.cache_clear()
    gemini.reset_cooldown()
    try:
        with respx.mock() as mock:
            route = mock.post(GEMINI_URL).mock(return_value=httpx.Response(429, json={"error": "quota"}))
            with caplog.at_level("WARNING"):
                result = gemini.extract(b"sample", "image/png", "test prompt")

        assert result is None
        assert route.call_count == 1
        assert "quota" in caplog.text.lower()
        assert secret not in caplog.text
    finally:
        gemini.reset_cooldown()
        get_settings.cache_clear()
