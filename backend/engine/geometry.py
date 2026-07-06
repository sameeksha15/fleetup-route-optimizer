"""Route geometry providers — the road-following path drawn on the map.

Every provider degrades to a straight line on any error, so the map always
renders something even when an external routing service is unreachable.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from .routing_api import LatLon, OSRMClient, RoutingApiError, TomTomClient


class GeometryProvider(ABC):
    name: str

    @abstractmethod
    def path(self, ordered_points: Sequence[LatLon]) -> list[list[float]]:
        """Road geometry through the ordered points, as [lat, lon] pairs."""


def _straight(points: Sequence[LatLon]) -> list[list[float]]:
    return [[lat, lon] for lat, lon in points]


class StraightLineGeometry(GeometryProvider):
    """Direct segments between stops — the zero-dependency fallback."""

    name = "straight"

    def path(self, ordered_points: Sequence[LatLon]) -> list[list[float]]:
        return _straight(ordered_points)


class OSRMGeometry(GeometryProvider):
    """Road-following geometry from OSRM (free, no key)."""

    name = "osrm"

    def __init__(self, client: OSRMClient):
        self.client = client

    def path(self, ordered_points: Sequence[LatLon]) -> list[list[float]]:
        try:
            return self.client.route(ordered_points)
        except RoutingApiError:
            return _straight(ordered_points)


class TomTomGeometry(GeometryProvider):
    """Traffic-aware road geometry from TomTom (requires a key)."""

    name = "tomtom"

    def __init__(self, client: TomTomClient):
        self.client = client

    def path(self, ordered_points: Sequence[LatLon]) -> list[list[float]]:
        try:
            return self.client.route(ordered_points)
        except RoutingApiError:
            return _straight(ordered_points)
