"""Geocoding: cache behaviour with the network mocked (no real Nominatim calls)."""

import app.services.geocoding as geo


class _FakeResp:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


def _patch(monkeypatch, data, counter):
    monkeypatch.setattr(geo, "_MIN_INTERVAL_S", 0.0)  # no throttling in tests

    def fake_get(*args, **kwargs):
        counter["n"] += 1
        return _FakeResp(data)

    monkeypatch.setattr(geo.requests, "get", fake_get)


def test_geocode_hit_is_cached(client, monkeypatch):
    calls = {"n": 0}
    _patch(monkeypatch, [{"lat": "19.10", "lon": "72.90"}], calls)

    first = client.post("/api/geocode", json={"address": "Link Road, Andheri"}).json()
    assert first["found"] is True and first["latitude"] == 19.10

    # Same address (normalized) -> served from the DB cache, no second network call.
    second = client.post("/api/geocode", json={"address": "link road,   andheri"}).json()
    assert second["latitude"] == 19.10
    assert calls["n"] == 1


def test_geocode_miss_is_cached(client, monkeypatch):
    calls = {"n": 0}
    _patch(monkeypatch, [], calls)  # Nominatim returns nothing

    first = client.post("/api/geocode", json={"address": "Nowhere at all xyz"}).json()
    assert first["found"] is False
    second = client.post("/api/geocode", json={"address": "Nowhere at all xyz"}).json()
    assert second["found"] is False
    assert calls["n"] == 1  # the miss was remembered
