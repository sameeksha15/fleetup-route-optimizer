from datetime import datetime

import numpy as np

from engine.entities import Stop
from engine.routing_api import OSRMClient, RoutingApiError, TomTomClient
from engine.travel_time import OfflineEstimator, OSRMProvider, TomTomProvider

STOPS = [
    Stop(index=0, latitude=19.00, longitude=72.80),
    Stop(index=1, latitude=19.10, longitude=72.90),
    Stop(index=2, latitude=19.20, longitude=73.00),
]


def test_matrix_shape_and_diagonal():
    matrix = OfflineEstimator().matrix(STOPS, datetime(2026, 7, 3, 12, 0))
    assert matrix.shape == (3, 3)
    assert np.allclose(np.diag(matrix), 0.0)
    assert (matrix[matrix > 0] < 24 * 60).all()


def test_matrix_is_symmetric():
    matrix = OfflineEstimator().matrix(STOPS, datetime(2026, 7, 3, 12, 0))
    assert np.allclose(matrix, matrix.T)


def test_peak_hours_are_slower():
    estimator = OfflineEstimator()
    off_peak = estimator.matrix(STOPS, datetime(2026, 7, 3, 13, 0))
    peak = estimator.matrix(STOPS, datetime(2026, 7, 3, 9, 0))
    assert peak[0][1] > off_peak[0][1]


def test_osrm_provider_uses_table(monkeypatch):
    fake = np.array([[0, 10, 20], [10, 0, 10], [20, 10, 0]], dtype=float)
    client = OSRMClient()
    monkeypatch.setattr(client, "table", lambda coords: (fake, fake))
    matrix = OSRMProvider(client).matrix(STOPS, datetime(2026, 7, 3, 12, 0))
    assert np.array_equal(matrix, fake)


def test_osrm_provider_falls_back_on_error(monkeypatch):
    def boom(coords):
        raise RoutingApiError("service down")

    client = OSRMClient()
    monkeypatch.setattr(client, "table", boom)
    offline = OfflineEstimator()
    matrix = OSRMProvider(client, fallback=offline).matrix(STOPS, datetime(2026, 7, 3, 12, 0))
    assert np.allclose(matrix, offline.matrix(STOPS, datetime(2026, 7, 3, 12, 0)))


def test_provider_time_sensitivity_flags():
    # Only traffic/time-of-day-aware providers get per-trip matrices.
    assert OfflineEstimator().time_sensitive is True
    assert OSRMProvider(OSRMClient()).time_sensitive is False
    assert TomTomProvider(TomTomClient("key")).time_sensitive is True


def test_tomtom_provider_passes_departure_time(monkeypatch):
    captured = {}

    def fake_table(coords, depart_at):
        captured["depart_at"] = depart_at
        return np.zeros((len(STOPS), len(STOPS)))

    client = TomTomClient("key")
    monkeypatch.setattr(client, "table", fake_table)
    when = datetime(2026, 7, 3, 15, 30)
    TomTomProvider(client).matrix(STOPS, when)
    assert captured["depart_at"] == when


def test_tomtom_provider_falls_back_on_error(monkeypatch):
    def boom(coords, depart_at):
        raise RoutingApiError("rate limited")

    client = TomTomClient("key")
    monkeypatch.setattr(client, "table", boom)
    offline = OfflineEstimator()
    at = datetime(2026, 7, 3, 12, 0)
    matrix = TomTomProvider(client, fallback=offline).matrix(STOPS, at)
    assert np.allclose(matrix, offline.matrix(STOPS, at))
