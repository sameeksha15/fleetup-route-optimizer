"""Domain entities shared across the engine."""

from __future__ import annotations

from dataclasses import dataclass, field

from .geo import haversine_km


@dataclass(frozen=True)
class Warehouse:
    id: int
    name: str
    latitude: float
    longitude: float


@dataclass(frozen=True)
class TimeWindow:
    """Delivery window in minutes since midnight."""

    start_min: int
    end_min: int

    def contains(self, minute: float) -> bool:
        return self.start_min <= minute <= self.end_min


@dataclass
class Package:
    id: int
    address: str
    latitude: float
    longitude: float
    weight_kg: float
    volume_m3: float
    priority: int  # 0 = low, 1 = medium, 2 = high
    window: TimeWindow
    warehouse_id: int | None = None
    cluster: int | None = None
    # Parcel dimensions (cm), optional; used for the physical fit check.
    length_cm: float | None = None
    width_cm: float | None = None
    height_cm: float | None = None

    @property
    def dimensions_cm(self) -> tuple[float, float, float] | None:
        if None in (self.length_cm, self.width_cm, self.height_cm):
            return None
        return (self.length_cm, self.width_cm, self.height_cm)


@dataclass
class Truck:
    id: int
    capacity_kg: float
    volume_m3: float
    warehouse_id: int
    latitude: float
    longitude: float
    packages: list[Package] = field(default_factory=list)
    # Internal cargo-bay dimensions (cm), optional.
    length_cm: float | None = None
    width_cm: float | None = None
    height_cm: float | None = None

    @property
    def used_capacity_kg(self) -> float:
        return sum(p.weight_kg for p in self.packages)

    @property
    def used_volume_m3(self) -> float:
        return sum(p.volume_m3 for p in self.packages)

    @property
    def remaining_capacity_kg(self) -> float:
        return self.capacity_kg - self.used_capacity_kg

    @property
    def remaining_volume_m3(self) -> float:
        return self.volume_m3 - self.used_volume_m3

    @property
    def dimensions_cm(self) -> tuple[float, float, float] | None:
        if None in (self.length_cm, self.width_cm, self.height_cm):
            return None
        return (self.length_cm, self.width_cm, self.height_cm)

    def fits_dimensions(self, package: Package) -> bool:
        """Can this parcel physically fit the cargo bay, allowing any rotation?

        Sort both dimension triples and require each parcel side to fit the
        corresponding bay side. Unknown dimensions (truck or parcel) don't gate.
        """
        parcel = package.dimensions_cm
        bay = self.dimensions_cm
        if parcel is None or bay is None:
            return True
        return all(p <= b for p, b in zip(sorted(parcel), sorted(bay)))

    def try_load(self, package: Package) -> bool:
        """Load the package if it fits within weight, volume, and dimension limits."""
        if (
            self.remaining_capacity_kg >= package.weight_kg
            and self.remaining_volume_m3 >= package.volume_m3
            and self.fits_dimensions(package)
        ):
            self.packages.append(package)
            return True
        return False


@dataclass(frozen=True)
class Stop:
    """A node on a truck's route. Index 0 is always the depot."""

    index: int
    latitude: float
    longitude: float
    package_id: int | None = None
    priority: int = 0
    window: TimeWindow | None = None

    @property
    def is_depot(self) -> bool:
        return self.package_id is None

    def distance_km_to(self, other: "Stop") -> float:
        return haversine_km(self.latitude, self.longitude, other.latitude, other.longitude)


@dataclass(frozen=True)
class Visit:
    """One event on a truck's executed schedule."""

    kind: str  # "depart" | "delivery" | "failed" | "reload" | "break" | "return"
    trip_number: int
    package_id: int | None
    latitude: float
    longitude: float
    eta_min: float  # arrival (or event start)
    departure_min: float  # when the truck moves on
    window: TimeWindow | None = None
    on_time: bool | None = None  # deliveries only


@dataclass
class TruckPlan:
    truck_id: int
    warehouse_id: int
    visits: list[Visit] = field(default_factory=list)
    drive_min: float = 0.0
    distance_km: float = 0.0
    waiting_min: float = 0.0
    overtime_min: float = 0.0
    stops_served: int = 0
    failed: int = 0
    trips: int = 0
    cost_breakdown: dict[str, float] = field(default_factory=dict)
