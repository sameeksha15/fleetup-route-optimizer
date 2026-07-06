"""Address -> coordinates via free OpenStreetMap / Nominatim, cached in the DB.

Warehouses are placed by hand on a map; this exists for *order* addresses coming
from a form or a bulk import. Results (hits and misses) are cached so a repeated
address never hits the network, and calls are throttled to respect Nominatim's
usage policy. Every failure degrades to ``None`` — the caller flags the row for
manual fixing rather than crashing the import.
"""

from __future__ import annotations

import threading
import time

import requests
from sqlalchemy.orm import Session

from .. import models
from ..config import get_settings

# Bias results toward the Mumbai / Navi Mumbai / Thane region.
# viewbox = left,top,right,bottom  (lon_min, lat_max, lon_max, lat_min)
_VIEWBOX = "72.75,19.35,73.15,18.85"
_MIN_INTERVAL_S = 1.1  # Nominatim asks for <= 1 request/second

_throttle_lock = threading.Lock()
_last_call = 0.0


def normalize(address: str) -> str:
    return " ".join(address.split()).strip().lower()


def _respect_rate_limit() -> None:
    global _last_call
    with _throttle_lock:
        wait = _MIN_INTERVAL_S - (time.monotonic() - _last_call)
        if wait > 0:
            time.sleep(wait)
        _last_call = time.monotonic()


def _query_nominatim(address: str) -> tuple[float, float] | None:
    settings = get_settings()
    _respect_rate_limit()
    try:
        resp = requests.get(
            settings.geocoder_base_url,
            params={
                "q": address,
                "format": "json",
                "limit": 1,
                "countrycodes": "in",
                "viewbox": _VIEWBOX,
            },
            headers={"User-Agent": settings.geocoder_user_agent},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json()
    except (requests.RequestException, ValueError):
        return None
    if not results:
        return None
    try:
        return float(results[0]["lat"]), float(results[0]["lon"])
    except (KeyError, ValueError, TypeError):
        return None


def geocode(db: Session, address: str) -> tuple[float, float] | None:
    """Resolve an address to (lat, lon), using and updating the shared cache."""
    query = normalize(address)
    if not query:
        return None

    cached = db.query(models.GeocodeCache).filter(models.GeocodeCache.query == query).first()
    if cached is not None:
        if cached.found:
            return cached.latitude, cached.longitude
        return None

    result = _query_nominatim(query)
    entry = models.GeocodeCache(
        query=query,
        found=result is not None,
        latitude=result[0] if result else None,
        longitude=result[1] if result else None,
    )
    db.add(entry)
    db.commit()
    return result
