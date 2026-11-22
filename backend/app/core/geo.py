"""Pure geo helpers: haversine distance and point-in-circle membership.

No I/O, no dependencies - used by exposure (zone membership), matching
(min_separation_km) and the demo world. Radii and distances stay in metres/km
and every caller states which unit it is passing.
"""

from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon points, in kilometres."""
    phi1 = radians(lat1)
    phi2 = radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlambda / 2) ** 2
    return 2.0 * EARTH_RADIUS_KM * asin(sqrt(a))


def point_in_circle(lat: float, lon: float, center_lat: float, center_lon: float, radius_m: float) -> bool:
    """True if the point lies within `radius_m` metres of the circle centre.

    Zone membership for curated circular planning zones (hazard_zones), not an
    official flood map - the honest-labelling rule (R9) applies wherever this
    result reaches a user.
    """
    return haversine_km(lat, lon, center_lat, center_lon) * 1000.0 <= radius_m