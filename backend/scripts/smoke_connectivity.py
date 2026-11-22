"""Phase 0 connectivity smoke test (throw-away diagnostic, not application code).

Checks the four external calls the build depends on and prints what came back:
  a) Open-Meteo forecast
  b) Open-Meteo archive (Cyclone Michaung window, 2023-12-03)
  c) Open-Meteo elevation
  d) Gemini free-tier generateContent with a tiny image, JSON output

Never raises: every check reports ok/error so the run always finishes. Results are
transcribed into docs/VERIFIED_FACTS.md.
"""

from __future__ import annotations

import base64
import io
import json
import os
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
LAT, LON = 13.100, 80.155
TIMEOUT = 25.0


def _load_env() -> None:
    """Load backend/.env if python-dotenv is available; never fail the script."""
    try:
        from dotenv import load_dotenv
    except Exception:
        return
    env_path = ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)


def _summarise_precip(payload: dict) -> dict:
    times = payload.get("hourly", {}).get("time", []) or []
    vals = payload.get("hourly", {}).get("precipitation", []) or []
    nums = [v for v in vals if isinstance(v, (int, float))]
    return {
        "hours": len(times),
        "first_time": times[0] if times else None,
        "last_time": times[-1] if times else None,
        "total_mm": round(sum(nums), 2) if nums else 0.0,
        "max_hourly_mm": max(nums) if nums else 0.0,
    }


def check_forecast() -> dict:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LAT,
        "longitude": LON,
        "hourly": "precipitation",
        "forecast_days": 3,
        "timezone": "UTC",
    }
    with httpx.Client(timeout=TIMEOUT) as c:
        r = c.get(url, params=params)
    out = {"status": r.status_code, "url": str(r.request.url)}
    if r.status_code == 200:
        out["data"] = _summarise_precip(r.json())
    else:
        out["body"] = r.text[:400]
    return out


def check_archive() -> dict:
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": LAT,
        "longitude": LON,
        "start_date": "2023-12-03",
        "end_date": "2023-12-03",
        "hourly": "precipitation",
        "timezone": "UTC",
    }
    with httpx.Client(timeout=TIMEOUT) as c:
        r = c.get(url, params=params)
    out = {"status": r.status_code, "url": str(r.request.url)}
    if r.status_code == 200:
        out["data"] = _summarise_precip(r.json())
    else:
        out["body"] = r.text[:400]
    return out


def check_elevation() -> dict:
    url = "https://api.open-meteo.com/v1/elevation"
    params = {"latitude": f"{LAT},{LAT + 0.01}", "longitude": f"{LON},{LON + 0.01}"}
    with httpx.Client(timeout=TIMEOUT) as c:
        r = c.get(url, params=params)
    out = {"status": r.status_code, "url": str(r.request.url)}
    if r.status_code == 200:
        out["data"] = r.json()
    else:
        out["body"] = r.text[:400]
    return out


def _tiny_png_b64() -> str:
    """64x64 white PNG with a black rectangle, via Pillow."""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (64, 64), "white")
    ImageDraw.Draw(img).rectangle([16, 20, 48, 28], fill="black")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def check_gemini() -> dict:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    model = os.environ.get("GEMINI_MODEL", "").strip()
    if not key:
        return {"status": "SKIPPED", "reason": "GEMINI_API_KEY not set in backend/.env"}
    if not model:
        return {"status": "SKIPPED", "reason": "GEMINI_MODEL not set (check AI Studio free tier)"}

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {
        "contents": [
            {
                "parts": [
                    {"text": 'Return only JSON: {"ok": true, "shapes": <number of black shapes you see>}'},
                    {
                        "inline_data": {
                            "mime_type": "image/png",
                            "data": _tiny_png_b64(),
                        }
                    },
                ]
            }
        ],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
    }
    t0 = time.time()
    with httpx.Client(timeout=40.0) as c:
        r = c.post(url, params={"key": key}, json=body)
    out = {"status": r.status_code, "model": model, "latency_ms": int((time.time() - t0) * 1000)}
    if r.status_code == 200:
        text = r.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text")
        out["text"] = (text or "")[:600]
    else:
        out["body"] = r.text[:600]
    return out


def main() -> int:
    _load_env()
    results: dict[str, dict] = {}
    for name, fn in (
        ("forecast", check_forecast),
        ("archive", check_archive),
        ("elevation", check_elevation),
        ("gemini", check_gemini),
    ):
        try:
            results[name] = fn()
        except Exception as exc:  # noqa: BLE001 - diagnostic script
            results[name] = {"status": "ERROR", "error": f"{type(exc).__name__}: {exc}"}

    print(json.dumps(results, indent=2, default=str))

    failed = [k for k, v in results.items() if v.get("status") == "ERROR"]
    if failed:
        print(f"\nFAILED: {failed}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())