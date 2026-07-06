"""HTTP clients for external routing services (OSRM, TomTom).

Both expose the same two capabilities:
- ``table``   — pairwise travel-time (and distance) matrices for optimization.
- ``route``   — the road-following geometry of an ordered path, for drawing.

Results are cached in-process by coordinate sequence so repeated runs over the
same stops don't re-hit the network. Callers are expected to handle
``RoutingApiError`` and fall back (usually to straight lines / the offline
estimator).
"""

from __future__ import annotations

import time
from collections.abc import Sequence

import numpy as np
import requests

LatLon = tuple[float, float]


class RoutingApiError(RuntimeError):
    """Raised when an external routing service cannot fulfil a request."""


def _round_key(coords: Sequence[LatLon]) -> tuple:
    return tuple((round(lat, 5), round(lon, 5)) for lat, lon in coords)


class OSRMClient:
    """OSRM (Open Source Routing Machine) HTTP client.

    Defaults to the public demo server. Point ``base_url`` at a self-hosted
    instance for production use.
    """

    def __init__(self, base_url: str = "https://router.project-osrm.org", timeout_s: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s
        self._route_cache: dict[tuple, list[list[float]]] = {}
        self._table_cache: dict[tuple, tuple[np.ndarray, np.ndarray]] = {}

    def _coords_param(self, coords: Sequence[LatLon]) -> str:
        # OSRM takes lon,lat pairs separated by semicolons.
        return ";".join(f"{lon},{lat}" for lat, lon in coords)

    def table(self, coords: Sequence[LatLon]) -> tuple[np.ndarray, np.ndarray]:
        """Return (minutes, km) matrices for all coordinate pairs."""
        key = _round_key(coords)
        if key in self._table_cache:
            return self._table_cache[key]
        url = f"{self.base_url}/table/v1/driving/{self._coords_param(coords)}"
        try:
            resp = requests.get(
                url, params={"annotations": "duration,distance"}, timeout=self.timeout_s
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            raise RoutingApiError(f"OSRM table request failed: {exc}") from exc
        if data.get("code") != "Ok" or "durations" not in data:
            raise RoutingApiError(f"OSRM table returned {data.get('code')!r}")

        minutes = np.array(data["durations"], dtype=float) / 60.0
        distances = data.get("distances")
        km = np.array(distances, dtype=float) / 1000.0 if distances else np.zeros_like(minutes)
        if np.isnan(minutes).any():
            raise RoutingApiError("OSRM table contains unreachable pairs")
        self._table_cache[key] = (minutes, km)
        return minutes, km

    def route(self, coords: Sequence[LatLon]) -> list[list[float]]:
        """Return the road geometry through ``coords`` in order, as [lat, lon] points."""
        if len(coords) < 2:
            return [[lat, lon] for lat, lon in coords]
        key = _round_key(coords)
        if key in self._route_cache:
            return self._route_cache[key]
        url = f"{self.base_url}/route/v1/driving/{self._coords_param(coords)}"
        try:
            resp = requests.get(
                url, params={"overview": "full", "geometries": "geojson"}, timeout=self.timeout_s
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            raise RoutingApiError(f"OSRM route request failed: {exc}") from exc
        if data.get("code") != "Ok" or not data.get("routes"):
            raise RoutingApiError(f"OSRM route returned {data.get('code')!r}")

        # GeoJSON coordinates are [lon, lat]; the app works in [lat, lon].
        line = data["routes"][0]["geometry"]["coordinates"]
        geometry = [[lat, lon] for lon, lat in line]
        self._route_cache[key] = geometry
        return geometry


class TomTomClient:
    """TomTom client: live-traffic matrix and road geometry (requires an API key)."""

    MATRIX_URL = "https://api.tomtom.com/routing/matrix/2/async"
    ROUTE_URL = "https://api.tomtom.com/routing/1/calculateRoute"
    POLL_INTERVAL_S = 2
    POLL_ATTEMPTS = 30

    def __init__(self, api_key: str, timeout_s: float = 30.0):
        if not api_key:
            raise ValueError("TomTom client requires an API key")
        self.api_key = api_key
        self.timeout_s = timeout_s
        self._route_cache: dict[tuple, list[list[float]]] = {}

    def table(self, coords: Sequence[LatLon], depart_at) -> np.ndarray:
        """Live-traffic travel-time matrix in minutes (async Matrix Routing v2)."""
        points = [{"point": {"latitude": lat, "longitude": lon}} for lat, lon in coords]
        body = {
            "origins": points,
            "destinations": points,
            "options": {
                "departAt": depart_at.strftime("%Y-%m-%dT%H:%M:%S"),
                "routeType": "fastest",
                "traffic": "live",
                "travelMode": "car",
            },
        }
        try:
            resp = requests.post(
                f"{self.MATRIX_URL}?key={self.api_key}", json=body, timeout=self.timeout_s
            )
            resp.raise_for_status()
            job_id = resp.json().get("jobId")
            if not job_id:
                raise RoutingApiError("TomTom matrix submission returned no job id")

            result_url = f"{self.MATRIX_URL}/{job_id}/result?key={self.api_key}"
            data = None
            for _ in range(self.POLL_ATTEMPTS):
                poll = requests.get(result_url, timeout=self.timeout_s)
                if poll.status_code == 200:
                    data = poll.json()
                    break
                if poll.status_code not in (202, 404):
                    poll.raise_for_status()
                time.sleep(self.POLL_INTERVAL_S)
        except requests.RequestException as exc:
            raise RoutingApiError(f"TomTom matrix request failed: {exc}") from exc
        if data is None:
            raise RoutingApiError("TomTom matrix job did not complete in time")

        n = len(coords)
        minutes = np.full((n, n), np.inf)
        np.fill_diagonal(minutes, 0.0)
        for entry in data.get("data", []):
            seconds = entry.get("routeSummary", {}).get("travelTimeInSeconds")
            if seconds is not None:
                minutes[entry["originIndex"]][entry["destinationIndex"]] = seconds / 60.0
        if np.isinf(minutes).any():
            raise RoutingApiError("TomTom matrix result is incomplete")
        return minutes

    def route(self, coords: Sequence[LatLon]) -> list[list[float]]:
        """Road geometry through ``coords`` in order, as [lat, lon] points."""
        if len(coords) < 2:
            return [[lat, lon] for lat, lon in coords]
        key = _round_key(coords)
        if key in self._route_cache:
            return self._route_cache[key]
        locations = ":".join(f"{lat},{lon}" for lat, lon in coords)
        url = f"{self.ROUTE_URL}/{locations}/json"
        try:
            resp = requests.get(
                url,
                params={
                    "key": self.api_key,
                    "routeRepresentation": "polyline",
                    "traffic": "true",
                    "travelMode": "car",
                },
                timeout=self.timeout_s,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            raise RoutingApiError(f"TomTom route request failed: {exc}") from exc
        routes = data.get("routes")
        if not routes:
            raise RoutingApiError("TomTom route returned no routes")

        geometry: list[list[float]] = []
        for leg in routes[0].get("legs", []):
            for pt in leg.get("points", []):
                geometry.append([pt["latitude"], pt["longitude"]])
        if not geometry:
            raise RoutingApiError("TomTom route contained no points")
        self._route_cache[key] = geometry
        return geometry
