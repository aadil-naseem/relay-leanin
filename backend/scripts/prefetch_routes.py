"""One-time access-route prefetch with OSMnx + OpenStreetMap (Phase 4, task 3).

Downloads the drivable network around Chennai metro ONCE (cached under
data/raw/, git-ignored), then for each Chennai-metro site and each configured
exit junction computes the shortest drivable route, samples it every ~250 m,
fetches elevations for the samples (batched), flags samples below the cluster's
25th-percentile elevation, and counts underpass segments (tunnel or negative
layer). Also measures each site's distance to the nearest OSM waterway/water
body and writes it back into terrain.json.

Route scope decision (recorded): only sites inside the Michaung storm footprint
(Ambattur cluster + Guindy) get routes - the far partners (Oragadam, Hosur,
Peenya, Coimbatore) are never exposed in this story and their route facts stay
null (schema supports it; M4 falls back to site-only exposure).

Data (c) OpenStreetMap contributors, ODbL. Runtime never calls this script.

Usage: python scripts/prefetch_routes.py
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

import networkx as nx  # noqa: E402
import osmnx as ox  # noqa: E402

from app.config_loader import load_configs  # noqa: E402

CACHE_DIR = BACKEND_DIR / "data" / "cache"
RAW_DIR = BACKEND_DIR / "data" / "raw"
GRAPH_PATH = RAW_DIR / "graph_chennai.graphml"
ELEVATION_URL = "https://api.open-meteo.com/v1/elevation"
BATCH_LIMIT = 100  # verified live
SAMPLE_SPACING_M = 250.0
WATER_SEARCH_M = 3000

# Chennai-metro bbox: (west, south, east, north) - covers the Ambattur cluster
# and Guindy with margin.
BBOX = (80.10, 12.96, 80.28, 13.17)


def _fetch_elevations(points: list[tuple[float, float]]) -> list[float]:
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
            raise RuntimeError(f"elevation API returned {len(values)} of {len(batch)}")
        elevations.extend(float(v) for v in values)
    return elevations


def _load_or_download_graph():
    if GRAPH_PATH.exists():
        print(f"loading cached graph {GRAPH_PATH}")
        return ox.load_graphml(GRAPH_PATH)
    # keep the layer tag so underpass counting sees negative layers
    ox.settings.useful_tags_way = list(ox.settings.useful_tags_way) + ["layer"]
    print(f"downloading drive graph for bbox {BBOX} (one-time)...")
    graph = ox.graph_from_bbox(bbox=BBOX, network_type="drive", simplify=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    ox.save_graphml(graph, GRAPH_PATH)
    print(f"saved {GRAPH_PATH} ({graph.number_of_nodes()} nodes)")
    return graph


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


class _NodeIndex:
    """Nearest-node lookup without scikit-learn (osmnx.optional dep avoided).

    Vectorised haversine over every graph node; 77k nodes x ~15 queries is
    trivial, and this is a one-time prefetch, not runtime code.
    """

    def __init__(self, graph) -> None:
        import numpy as np

        self.ids: list[int] = []
        lats: list[float] = []
        lons: list[float] = []
        for node_id, data in graph.nodes(data=True):
            self.ids.append(node_id)
            lats.append(data["y"])
            lons.append(data["x"])
        self._lat = np.radians(np.array(lats))
        self._lon = np.radians(np.array(lons))

    def nearest(self, lat: float, lon: float):
        import numpy as np

        p = math.radians(lat)
        lon_r = math.radians(lon)
        dlat = self._lat - p
        dlon = self._lon - lon_r
        a = np.sin(dlat / 2) ** 2 + math.cos(p) * np.cos(self._lat) * np.sin(dlon / 2) ** 2
        return self.ids[int(np.argmin(2 * np.arcsin(np.sqrt(a))))]


def _sample_path(coords: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Walk the path and return points every SAMPLE_SPACING_M."""
    if len(coords) < 2:
        return coords
    samples = [coords[0]]
    target = SAMPLE_SPACING_M
    travelled = 0.0
    for (lat1, lon1), (lat2, lon2) in zip(coords, coords[1:]):
        seg = _haversine_m(lat1, lon1, lat2, lon2)
        if seg == 0:
            continue
        while travelled + seg >= target:
            frac = (target - travelled) / seg
            samples.append((lat1 + (lat2 - lat1) * frac, lon1 + (lon2 - lon1) * frac))
            target += SAMPLE_SPACING_M
        travelled += seg
    if samples[-1] != coords[-1]:
        samples.append(coords[-1])
    return samples


def _edge_is_underpass(graph, u, v) -> bool:
    data = graph.get_edge_data(u, v) or {}
    for attrs in data.values():
        tunnel = attrs.get("tunnel")
        layer = attrs.get("layer")
        if tunnel not in (None, "", "no", False):
            return True
        try:
            if layer is not None and float(layer) < 0:
                return True
        except (TypeError, ValueError):
            pass
    return False


def _nearest_water_m(lat: float, lon: float) -> float | None:
    """Distance from the site point to the nearest OSM water feature, metres."""
    try:
        tags = {"natural": ["water", "bay", "riverbank"], "waterway": True}
        features = ox.features_from_point((lat, lon), tags, dist=WATER_SEARCH_M)
        if features.empty:
            return None
        projected = ox.projection.project_gdf(features)
        point = ox.projection.project_gdf(
            __import__("geopandas").GeoDataFrame(
                geometry=[__import__("shapely").geometry.Point(lon, lat)],
                crs="EPSG:4326",
            )
        )
        distances = projected.geometry.distance(point.geometry.iloc[0])
        return round(float(distances.min()), 1)
    except Exception as error:  # noqa: BLE001 - water is optional; honest null on failure
        print(f"  water lookup failed: {type(error).__name__}: {error}")
        return None


def main() -> int:
    bundle = load_configs()
    terrain_path = CACHE_DIR / "terrain.json"
    terrain = json.loads(terrain_path.read_text(encoding="utf-8"))
    low_threshold = terrain["low_threshold_m"]

    exits_by_cluster = {cluster: list(exits) for cluster, exits in bundle.cluster.exits.items()}
    route_sites = [s for s in bundle.cluster.sites if s.cluster_id in exits_by_cluster]
    print(f"routes: {len(route_sites)} sites, exits per cluster: "
          f"{ {c: len(e) for c, e in exits_by_cluster.items()} }")

    graph = _load_or_download_graph()
    node_index = _NodeIndex(graph)

    # --- compute all routes first (samples without elevations) ---
    planned: list[dict] = []
    all_sample_points: list[tuple[float, float]] = []
    for site in route_sites:
        site_exits = exits_by_cluster[site.cluster_id]
        orig = node_index.nearest(site.lat, site.lon)
        for exit_junction in site_exits:
            dest = node_index.nearest(exit_junction.lat, exit_junction.lon)
            path = nx.shortest_path(graph, orig, dest, weight="length")
            coords = [
                (graph.nodes[node]["y"], graph.nodes[node]["x"]) for node in path
            ]
            length_km = sum(
                _haversine_m(a[0], a[1], b[0], b[1]) for a, b in zip(coords, coords[1:])
            ) / 1000
            samples = _sample_path(coords)[1:-1]  # drop exact endpoints
            underpasses = sum(
                1 for u, v in zip(path, path[1:]) if _edge_is_underpass(graph, u, v)
            )
            planned.append(
                {
                    "route_id": f"rt_{site.id}_{exit_junction.id}",
                    "site_id": site.id,
                    "exit_id": exit_junction.id,
                    "exit_name": exit_junction.name,
                    "length_km": round(length_km, 2),
                    "underpass_count": underpasses,
                    "samples": [
                        {"lat": round(lat, 5), "lon": round(lon, 5)} for lat, lon in samples
                    ],
                }
            )
            all_sample_points.extend(samples)
            print(f"  {planned[-1]['route_id']}: {length_km:.1f} km, {len(samples)} samples, "
                  f"{underpasses} underpasses")

    # --- batch-fetch elevations for every sample point ---
    print(f"fetching {len(all_sample_points)} sample elevations...")
    sample_elevations = _fetch_elevations(all_sample_points)
    cursor = 0
    for route in planned:
        count = len(route["samples"])
        for offset, elevation in enumerate(sample_elevations[cursor : cursor + count]):
            route["samples"][offset]["elevation_m"] = round(elevation, 1)
        lows = sum(
            1 for s in route["samples"] if s["elevation_m"] < low_threshold
        )
        route["low_share"] = round(lows / count, 3) if count else None
        cursor += count

    # --- nearest water per routed site, written back into terrain.json ---
    for site in route_sites:
        if terrain["sites"].get(site.id, {}).get("nearest_water_m") is None:
            distance = _nearest_water_m(site.lat, site.lon)
            terrain["sites"][site.id]["nearest_water_m"] = distance
            print(f"  {site.id}: nearest water {distance} m")

    payload = {
        "source": "openstreetmap-osmnx",
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "low_threshold_m": low_threshold,
        "sample_spacing_m": SAMPLE_SPACING_M,
        "routes": planned,
    }
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    out = CACHE_DIR / "routes.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    terrain_path.write_text(json.dumps(terrain, indent=2), encoding="utf-8")
    print(f"wrote {out} ({len(planned)} routes); updated nearest_water_m in terrain.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
