"""One-time replay weather prefetch via the Open-Meteo archive API (Phase 4, task 5).

Fetches hourly precipitation for the Michaung window (2023-12-03..2023-12-05,
72 h, series start verified in Phase 0 so the heavy onset lands ~37-40 h after
t=0) for every configured site, and writes data/cache/replay_michaung.json.
Also writes data/cache/synthetic_storm.json - a deterministically generated,
clearly-labelled synthetic profile used only as the last-resort weather mode
(R7 honesty: never passed off as real data).

The archive was verified live in Phase 0: Ambattur 2023-12-04 total 238.7 mm,
peak hour 19.6 mm. Runtime never calls this script.

Usage: python scripts/prefetch_replay.py
"""

from __future__ import annotations

import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.config_loader import load_configs  # noqa: E402

CACHE_DIR = BACKEND_DIR / "data" / "cache"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
START_DATE = "2023-12-03"  # series_start_utc per cluster.yaml / Phase 0 decision
END_DATE = "2023-12-05"  # inclusive -> 3*24 = 72 hourly values
SERIES_HOURS = 72


def _fetch_site(lat: float, lon: float) -> dict:
    params = (
        f"latitude={lat:.4f}&longitude={lon:.4f}"
        f"&start_date={START_DATE}&end_date={END_DATE}"
        "&hourly=precipitation&timezone=UTC"
    )
    url = f"{ARCHIVE_URL}?{params}"
    with urllib.request.urlopen(url, timeout=60) as response:  # noqa: S310 - fixed https URL
        payload = json.load(response)
    if payload.get("error"):
        raise RuntimeError(f"archive API error for ({lat},{lon}): {payload.get('reason')}")
    hourly = payload["hourly"]
    if len(hourly["time"]) != SERIES_HOURS or len(hourly["precipitation"]) != SERIES_HOURS:
        raise RuntimeError(
            f"archive returned {len(hourly['time'])} values for ({lat},{lon}); expected {SERIES_HOURS}"
        )
    return {
        "time": hourly["time"],
        "precipitation_mm": [float(v) if v is not None else 0.0 for v in hourly["precipitation"]],
        "total_mm": round(sum(float(v) for v in hourly["precipitation"]), 1),
        "peak_hour_mm": round(max(float(v) for v in hourly["precipitation"]), 1),
    }


def _synthetic_profile() -> list[float]:
    """Deterministic synthetic storm: ramps up to a 20 mm/h peak at hour 36,
    recedes to zero by hour 60. Clearly labelled synthetic at every use."""
    profile = []
    for hour in range(SERIES_HOURS):
        if hour < 24:
            mm = hour / 24 * 6.0
        elif hour < 40:
            mm = 6.0 + (hour - 24) / 16 * 14.0  # ramp to 20 mm/h peak at hour 36-40
        elif hour < 60:
            mm = 20.0 * (1 - (hour - 40) / 20)
        else:
            mm = 0.0
        profile.append(round(mm, 2))
    return profile


def main() -> int:
    bundle = load_configs()
    sites: list[tuple[str, float, float]] = [(s.id, s.lat, s.lon) for s in bundle.cluster.sites]
    sites += [(s.id, s.lat, s.lon) for s in bundle.cluster.backtest_flooded]
    sites += [(s.id, s.lat, s.lon) for s in bundle.cluster.backtest_not_flooded]
    print(f"replay prefetch: {len(sites)} sites x {SERIES_HOURS} h")

    site_series: dict[str, dict] = {}
    for site_id, lat, lon in sites:
        series = _fetch_site(lat, lon)
        site_series[site_id] = series
        print(f"  {site_id}: total {series['total_mm']:.1f} mm, peak {series['peak_hour_mm']:.1f} mm/h")

    owner = site_series["fac_owner"]
    if owner["peak_hour_mm"] < 10.0:
        print("WARNING: owner peak hour < 10 mm - archive too smooth, keep synthetic as last resort")
    dec4 = sum(owner["precipitation_mm"][24:48])
    print(f"fac_owner 2023-12-04 total: {dec4:.1f} mm (verified reference: 238.7 mm)")

    payload = {
        "event": "michaung_2023",
        "series_start_utc": f"{START_DATE}T00:00:00Z",
        "series_hours": SERIES_HOURS,
        "source": "open-meteo-archive",
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "sites": site_series,
    }
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    out = CACHE_DIR / "replay_michaung.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {out}")

    synthetic = {
        "event": "synthetic_storm",
        "series_start_utc": "2000-01-01T00:00:00Z",  # aligned by the consumer to t=0
        "series_hours": SERIES_HOURS,
        "source": "synthetic",
        "label": "SYNTHETIC SAMPLE - generated profile, not observed weather",
        "sites": {
            site_id: {
                "time": [f"t+{h:02d}:00" for h in range(SERIES_HOURS)],
                "precipitation_mm": _synthetic_profile(),
                "total_mm": round(sum(_synthetic_profile()), 1),
                "peak_hour_mm": max(_synthetic_profile()),
            }
            for site_id, _, _ in sites
        },
    }
    out_synth = CACHE_DIR / "synthetic_storm.json"
    out_synth.write_text(json.dumps(synthetic, indent=2), encoding="utf-8")
    print(f"wrote {out_synth}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
