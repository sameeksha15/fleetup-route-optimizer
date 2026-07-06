"""Driver working rules (minutes since midnight)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DriverRules:
    shift_start_min: int = 9 * 60
    shift_end_min: int = 18 * 60
    lunch_earliest_min: int = 13 * 60  # lunch is taken at the first stop after 1 PM
    lunch_duration_min: int = 30
    service_time_min: float = 5.0  # unloading / handoff per delivery
    failed_service_min: float = 3.0  # time lost when the customer is absent
    reload_time_min: float = 15.0  # loading the next wave at the depot
