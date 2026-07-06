"""Travel-time providers.

Every provider returns a symmetric-shaped (n x n) matrix of travel times in
minutes between stops. The offline estimator makes the whole pipeline runnable
without network access or API keys; the TomTom provider adds live traffic when
a key is configured.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime

import numpy as np

from .entities import Stop
from .routing_api import OSRMClient, RoutingApiError, TomTomClient


class TravelTimeError(RuntimeError):
    """Raised when a provider cannot produce a travel-time matrix."""


class TravelTimeProvider(ABC):
    name: str
    #: Whether travel times vary with the time of day. When True, the pipeline
    #: recomputes each trip's matrix at that trip's departure so morning and
    #: afternoon traffic differ; when False, a single matrix is reused.
    time_sensitive: bool = False

    @abstractmethod
    def matrix(self, stops: Sequence[Stop], depart_at: datetime) -> np.ndarray:
        """Pairwise travel times in minutes, zeros on the diagonal."""


class OfflineEstimator(TravelTimeProvider):
    """Deterministic estimate from great-circle distance.

    Distance is inflated by a road-winding factor, and speed is scaled down
    during Mumbai's peak traffic hours so departure time still matters.
    """

    name = "offline"
    time_sensitive = True  # speed drops during peak hours

    #: (start_hour, end_hour, speed multiplier)
    PEAK_HOURS = ((8, 11, 0.6), (17, 21, 0.55))

    def __init__(self, base_speed_kmh: float = 40.0, winding_factor: float = 1.3):
        self.base_speed_kmh = base_speed_kmh
        self.winding_factor = winding_factor

    def _speed_at(self, depart_at: datetime) -> float:
        for start, end, factor in self.PEAK_HOURS:
            if start <= depart_at.hour < end:
                return self.base_speed_kmh * factor
        return self.base_speed_kmh

    def matrix(self, stops: Sequence[Stop], depart_at: datetime) -> np.ndarray:
        speed = self._speed_at(depart_at)
        n = len(stops)
        times = np.zeros((n, n))
        for i in range(n):
            for j in range(i + 1, n):
                km = stops[i].distance_km_to(stops[j]) * self.winding_factor
                minutes = km / speed * 60
                times[i][j] = times[j][i] = minutes
        return times


class OSRMProvider(TravelTimeProvider):
    """Road-network travel times from OSRM's Table service (free, no key)."""

    name = "osrm"
    time_sensitive = False  # OSRM has no traffic model, so times don't vary by hour

    def __init__(self, client: OSRMClient, fallback: TravelTimeProvider | None = None):
        self.client = client
        self.fallback = fallback

    def matrix(self, stops: Sequence[Stop], depart_at: datetime) -> np.ndarray:
        try:
            minutes, _ = self.client.table([(s.latitude, s.longitude) for s in stops])
            return minutes
        except RoutingApiError:
            if self.fallback is not None:
                return self.fallback.matrix(stops, depart_at)
            raise


class TomTomProvider(TravelTimeProvider):
    """Live-traffic travel times via TomTom's Matrix Routing v2 API."""

    name = "tomtom"
    time_sensitive = True  # live + predictive traffic varies through the day

    def __init__(self, client: TomTomClient, fallback: TravelTimeProvider | None = None):
        self.client = client
        self.fallback = fallback

    def matrix(self, stops: Sequence[Stop], depart_at: datetime) -> np.ndarray:
        try:
            return self.client.table([(s.latitude, s.longitude) for s in stops], depart_at)
        except RoutingApiError:
            if self.fallback is not None:
                return self.fallback.matrix(stops, depart_at)
            raise
