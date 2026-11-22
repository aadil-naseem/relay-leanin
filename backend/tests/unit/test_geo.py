"""Phase 1: haversine and point-in-circle."""

from app.core.geo import haversine_km, point_in_circle


def test_haversine_chennai_to_bengaluru():
    # Chennai (13.0827, 80.2707) -> Bengaluru (12.9716, 77.5946) is ~292 km by road,
    # ~290 km great-circle. Wide tolerance guards against Earth-radius trivia.
    distance = haversine_km(13.0827, 80.2707, 12.9716, 77.5946)
    assert 280.0 < distance < 305.0


def test_haversine_zero_distance_for_same_point():
    assert haversine_km(13.1, 80.155, 13.1, 80.155) == 0.0


def test_haversine_symmetry():
    a = haversine_km(13.100, 80.155, 12.842, 79.952)
    b = haversine_km(12.842, 79.952, 13.100, 80.155)
    assert abs(a - b) < 1e-9


def test_point_in_circle_contains_and_excludes():
    centre = (13.100, 80.155)
    assert point_in_circle(13.100, 80.155, *centre, 5000) is True
    # Hosur is ~230 km from Ambattur - must never sit in the same 5 km zone.
    assert point_in_circle(12.740, 77.830, *centre, 5000) is False


def test_point_in_circle_boundary_is_metre_accurate():
    # 0.09 deg of longitude at 13N is ~9.8 km; 0.10 deg is ~10.9 km.
    assert point_in_circle(13.100, 80.245, 13.100, 80.155, 10_000) is True
    assert point_in_circle(13.100, 80.255, 13.100, 80.155, 10_000) is False