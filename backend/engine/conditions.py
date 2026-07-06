"""Weather conditions and their effect on travel times."""

from enum import Enum


class Weather(str, Enum):
    """Applies a fleet-wide travel-time multiplier (Mumbai monsoon reality)."""

    CLEAR = "clear"
    RAIN = "rain"
    STORM = "storm"

    @property
    def travel_multiplier(self) -> float:
        return {Weather.CLEAR: 1.0, Weather.RAIN: 1.35, Weather.STORM: 1.7}[self]

    @classmethod
    def from_wmo_code(cls, code: int) -> "Weather":
        """Map an Open-Meteo WMO weather code to a travel condition.

        Thunderstorm and violent showers -> STORM; drizzle/rain/snow -> RAIN;
        everything drier (clear, cloud, fog) -> CLEAR.
        See https://open-meteo.com/en/docs for the WMO code table.
        """
        if code >= 95 or code in (82, 86):  # thunderstorm / violent showers
            return cls.STORM
        if 51 <= code <= 86:  # drizzle, rain, snow, rain showers
            return cls.RAIN
        return cls.CLEAR
