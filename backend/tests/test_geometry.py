import numpy as np

from engine import routing_api
from engine.geometry import OSRMGeometry, StraightLineGeometry
from engine.routing_api import OSRMClient, RoutingApiError

POINTS = [(19.00, 72.80), (19.10, 72.90), (19.20, 73.00)]


def test_straight_line_returns_input_points():
    path = StraightLineGeometry().path(POINTS)
    assert path == [[19.00, 72.80], [19.10, 72.90], [19.20, 73.00]]


def _fake_get(payload):
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return payload

    return lambda *a, **k: FakeResponse()


def test_osrm_client_parses_route_and_flips_lonlat(monkeypatch):
    # OSRM returns [lon, lat]; the client must emit [lat, lon].
    payload = {
        "code": "Ok",
        "routes": [{"geometry": {"coordinates": [[72.80, 19.00], [72.85, 19.05], [72.90, 19.10]]}}],
    }
    monkeypatch.setattr(routing_api.requests, "get", _fake_get(payload))
    path = OSRMClient().route(POINTS)
    assert path[0] == [19.00, 72.80]
    assert path[-1] == [19.10, 72.90]


def test_osrm_client_parses_table(monkeypatch):
    payload = {
        "code": "Ok",
        "durations": [[0, 600, 1200], [600, 0, 600], [1200, 600, 0]],
        "distances": [[0, 5000, 10000], [5000, 0, 5000], [10000, 5000, 0]],
    }
    monkeypatch.setattr(routing_api.requests, "get", _fake_get(payload))
    minutes, km = OSRMClient().table(POINTS)
    assert minutes.shape == (3, 3)
    assert minutes[0][1] == 10.0  # 600s -> 10 min
    assert km[0][2] == 10.0  # 10000m -> 10 km


def test_geometry_provider_falls_back_to_straight_on_error(monkeypatch):
    def boom(*a, **k):
        raise RoutingApiError("service down")

    client = OSRMClient()
    monkeypatch.setattr(client, "route", boom)
    path = OSRMGeometry(client).path(POINTS)
    assert path == [[19.00, 72.80], [19.10, 72.90], [19.20, 73.00]]
