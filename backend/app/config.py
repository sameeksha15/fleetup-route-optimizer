"""Application settings, loaded from environment / .env file."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./fleet.db"
    cors_origins: list[str] = ["http://localhost:3000"]
    tomtom_api_key: str = ""  # set -> live-traffic times + geometry
    osrm_base_url: str = "https://router.project-osrm.org"  # free road geometry/times

    # Address geocoding for order import (free OpenStreetMap / Nominatim). Results
    # are cached in the DB; Nominatim's policy requires a descriptive User-Agent
    # and <=1 request/second, so imports of new addresses geocode sequentially.
    geocoder_base_url: str = "https://nominatim.openstreetmap.org/search"
    geocoder_user_agent: str = "FleetUp/1.0 (fleet route optimization demo)"

    # Auth / sessions. JWT_SECRET should be set in production; when empty a
    # random per-process secret is used (secure, but sessions reset on restart).
    jwt_secret: str = ""
    jwt_expire_hours: int = 168  # 7 days
    cookie_name: str = "fleetup_session"
    cookie_secure: bool = False  # set True when served over HTTPS


@lru_cache
def get_settings() -> Settings:
    return Settings()
