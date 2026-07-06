"""Geodesic helpers."""

from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_KM = 6371.0

# Urban road distance exceeds the great-circle distance by roughly this factor.
ROAD_WINDING_FACTOR = 1.3


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two coordinates in kilometres."""
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return EARTH_RADIUS_KM * 2 * asin(sqrt(a))
