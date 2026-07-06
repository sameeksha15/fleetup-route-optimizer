"""Live weather via Open-Meteo (free, no API key).

Resolves current conditions at the fleet's location into a :class:`Weather`
condition that scales travel times. Any network problem degrades gracefully to
clear weather so a run never fails on the weather lookup.
"""

from __future__ import annotations

import requests

from .conditions import Weather

CURRENT_WEATHER_URL = "https://api.open-meteo.com/v1/forecast"


def fetch_live_weather(latitude: float, longitude: float, timeout_s: float = 10.0) -> tuple[Weather, str]:
    """Return the current (condition, human-readable source) at a location."""
    try:
        resp = requests.get(
            CURRENT_WEATHER_URL,
            params={"latitude": latitude, "longitude": longitude, "current_weather": True},
            timeout=timeout_s,
        )
        resp.raise_for_status()
        current = resp.json()["current_weather"]
        code = int(current["weathercode"])
    except (requests.RequestException, KeyError, ValueError, TypeError):
        return Weather.CLEAR, "live weather unavailable — assumed clear"

    condition = Weather.from_wmo_code(code)
    return condition, f"live (Open-Meteo code {code})"
