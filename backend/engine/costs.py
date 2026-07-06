"""The cost model: the single definition of what "optimal" means.

Every solver (heuristic or RL) and every KPI is scored against this one
weighted objective, so runs are directly comparable.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CostModel:
    drive_weight: float = 1.0  # per minute of driving
    fuel_weight: float = 2.0  # per kilometre (fuel + wear proxy)
    trip_fixed_cost: float = 30.0  # per depot departure — discourages pointless returns
    waiting_weight: float = 0.2  # per minute idling (cheap, but not free)
    lateness_weight: float = 3.0  # per minute past the window, scaled by priority
    overtime_weight: float = 5.0  # per driver minute past shift end
    unserved_penalty: float = 500.0  # per undelivered package, scaled by priority

    @staticmethod
    def priority_multiplier(priority: int) -> float:
        """Priority 0/1/2 -> x1/x2/x4. High priority failures hurt exponentially."""
        return float(2**priority)

    def lateness_cost(self, minutes_late: float, priority: int) -> float:
        return self.lateness_weight * minutes_late * self.priority_multiplier(priority)

    def breakdown(
        self,
        drive_min: float,
        distance_km: float,
        departures: int,
        waiting_min: float,
        weighted_lateness_min: float,
        overtime_min: float,
        weighted_unserved: float,
    ) -> dict[str, float]:
        """Itemised cost. ``weighted_*`` inputs are already priority-scaled."""
        components = {
            "drive": self.drive_weight * drive_min,
            "fuel": self.fuel_weight * distance_km,
            "trips": self.trip_fixed_cost * departures,
            "waiting": self.waiting_weight * waiting_min,
            "lateness": self.lateness_weight * weighted_lateness_min,
            "overtime": self.overtime_weight * overtime_min,
            "unserved": self.unserved_penalty * weighted_unserved,
        }
        components = {key: round(value, 1) for key, value in components.items()}
        components["total"] = round(sum(components.values()), 1)
        return components
