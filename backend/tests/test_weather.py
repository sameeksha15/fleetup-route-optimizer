import requests

from engine import weather
from engine.conditions import Weather


def test_wmo_code_mapping():
    assert Weather.from_wmo_code(0) is Weather.CLEAR  # clear sky
    assert Weather.from_wmo_code(3) is Weather.CLEAR  # overcast
    assert Weather.from_wmo_code(61) is Weather.RAIN  # rain
    assert Weather.from_wmo_code(71) is Weather.RAIN  # snow
    assert Weather.from_wmo_code(95) is Weather.STORM  # thunderstorm
    assert Weather.from_wmo_code(82) is Weather.STORM  # violent rain showers


def test_fetch_live_weather_maps_response(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"current_weather": {"weathercode": 61}}

    monkeypatch.setattr(weather.requests, "get", lambda *a, **k: FakeResponse())
    condition, source = weather.fetch_live_weather(19.1, 72.9)
    assert condition is Weather.RAIN
    assert "live" in source


def test_fetch_live_weather_falls_back_on_error(monkeypatch):
    def boom(*a, **k):
        raise requests.ConnectionError("no network")

    monkeypatch.setattr(weather.requests, "get", boom)
    condition, source = weather.fetch_live_weather(19.1, 72.9)
    assert condition is Weather.CLEAR
    assert "unavailable" in source
