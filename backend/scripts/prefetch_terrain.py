"""One-time terrain prefetch via the Open-Meteo elevation API (Phase 4, task 2).

For every configured site (factories, vendors, suppliers, back-test sites):
samples elevation at the centre and on 3 rings (500/1000/2000 m x 8 bearings),
computes `ring_mean_m` and `relative_m = elev - ring_mean` (negative = in a
depression). Also samples a coarse 15x15 grid over the Chennai-metro cluster
bounding box and stores its 25th-percentile elevation as `low_threshold_m`
(the reference routes are compared against in M4).

Batch limit VERIFIED live 2026-11-14: 100 coordinates per call, HTTP 200
(docs/VERIFIED_FACTS.md). Output is committed to data/cache/terrain.json -
runtime never calls this script.

Usage: python scripts/prefetch_terrain.py
"""

from __future__ import annotations

import json
import math
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.config_loader import load_configs  # noqa: E402

CACHE_DIR = BACKEND_DIR / "data" / "cache"
ELEVATION_URL = "https://api.open-meteo.com/v1/elevation"
BATCH_LIMIT = 100  # verified live
RINGS_M = (500.0, 1000.0, 2000.0)
BEARINGS_DEG = tuple(range(0, 360, 45))  # 8 bearings
GRID_N = 15
M_PER_DEG_LAT = 111_320.0


def _fetch_elevations(points: list[tuple[float, float]]) -> list[float]:
    """Fetch elevations for [(lat, lon), ...] in verified batches of <= 100."""
    elevations: list[float] = []
    for start in range(0, len(points), BATCH_LIMIT):
        batch = points[start : start + BATCH_LIMIT]
        lats = ",".join(f"{lat:.4f}" for lat, _ in batch)
        lons = ",".join(f"{lon:.4f}" for _, lon in batch)
        url = f"{ELEVATION_URL}?latitude={lats}&longitude={lons}"
        with urllib.request.urlopen(url, timeout=60) as response:  # noqa: S310 - fixed https URL
            payload = json.load(response)
        if payload.get("error") or not isinstance(payload.get("elevation"), list):
            raise RuntimeError(f"elevation API error: {payload}")
        values = payload["elevation"]
        if len(values) != len(batch):
            raise RuntimeError(f"elevation API returned {len(values)} of {len(batch)} points")
        elevations.extend(float(v) for v in values)
    return elevations


def _ring_points(lat: float, lon: float, radius_m: float, bearing_deg: int) -> tuple[float, float]:
    dlat = radius_m * math.cos(math.radians(bearing_deg)) / M_PER_DEG_LAT
    dlon = radius_m * math.sin(math.radians(bearing_deg)) / (
        M_PER_DEG_LAT * math.cos(math.radians(lat))
    )
    return lat + dlat, lon + dlon


def _site_samples(lat: float, lon: float) -> list[tuple[float, float]]:
    """Centre + 3 rings x 8 bearings = 25 points."""
    points = [(lat, lon)]
    for radius in RINGS_M:
        for bearing in BEARINGS_DEG:
            points.append(_ring_points(lat, lon, radius, bearing))
    return points


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round(fraction * (len(ordered) - 1)))))
    return ordered[index]


def main() -> int:
    bundle = load_configs()
    sites: list[tuple[str, float, float]] = [
        (site.id, site.lat, site.lon) for site in bundle.cluster.sites
    ]
    sites += [(s.id, s.lat, s.lon) for s in bundle.cluster.backtest_flooded]
    sites += [(s.id, s.lat, s.lon) for s in bundle.cluster.backtest_not_flooded]
    print(f"terrain prefetch: {len(sites)} sites")

    # all ring/centre points, site by site
    site_terrain: dict[str, dict[str, object]] = {}
    for site_id, lat, lon in sites:
        samples = _site_samples(lat, lon)
        elevations = _fetch_elevations(samples)
        centre = elevations[0]
        ring_mean = sum(elevations[1:]) / len(elevations[1:])
        site_terrain[site_id] = {
            "lat": lat,
            "lon": lon,
            "elevation_m": centre,
            "ring_mean_m": round(ring_mean, 2),
            "relative_m": round(centre - ring_mean, 2),
            "nearest_water_m": None,  # filled by prefetch_routes.py (OSM waterways)
        }
        print(f"  {site_id}: elev {centre:.0f} m, relative {centre - ring_mean:+.1f} m")

    # coarse grid over the Chennai-metro cluster bbox -> 25th-percentile threshold
    chennai = [s for s in bundle.cluster.sites if s.grid_id == "grid_chennai_metro"]
    lats = [s.lat for s in chennai]
    lons = [s.lon for s in chennai]
    margin = 0.03  # ~3 km beyond the sites' extent
    lat_min, lat_max = min(lats) - margin, max(lats) + margin
    lon_min, lon_max = min(lons) - margin, max(lons) + margin
    grid: list[tuple[float, float]] = []
    for i in range(GRID_N):
        for j in range(GRID_N):
            grid.append(
                (
                    lat_min + (lat_max - lat_min) * i / (GRID_N - 1),
                    lon_min + (lon_max - lon_min) * j / (GRID_N - 1),
                )
            )
    grid_elevations = _fetch_elevations(grid)
    low_threshold = _percentile(grid_elevations, 0.25)
    print(f"cluster grid {GRID_N}x{GRID_N}: low_threshold_m (25th pct) = {low_threshold:.1f}")

    payload = {
        "source": "open-meteo-elevation",
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "low_threshold_m": round(low_threshold, 2),
        "grid_bbox": {
            "lat_min": lat_min,
            "lat_max": lat_max,
            "lon_min": lon_min,
            "lon_max": lon_max,
        },
        "sites": site_terrain,
    }
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    out = CACHE_DIR / "terrain.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
