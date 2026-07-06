"""End-to-end orchestration: packages -> allocation -> waves -> routes -> KPIs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime

import numpy as np

from .allocation import assign_nearest_warehouse, load_trucks
from .conditions import Weather
from .costs import CostModel
from .drivers import DriverRules
from .entities import Package, Stop, TimeWindow, Truck, TruckPlan, Warehouse
from .geometry import GeometryProvider, StraightLineGeometry
from .routing import build_context, chain_departures, sequence_waves
from .simulate import execute
from .travel_time import OfflineEstimator, TravelTimeProvider
from .waves import build_waves
from .weather import fetch_live_weather


@dataclass(frozen=True)
class DeliveryPoint:
    """A known delivery address served by a warehouse (seed data)."""

    address: str
    latitude: float
    longitude: float
    warehouse_id: int
    window: TimeWindow


@dataclass(frozen=True)
class PipelineConfig:
    seed: int = 42
    solver: str = "heuristic"  # "heuristic" | "dqn"
    weather_mode: str = "live"  # "live" | "clear" | "rain" | "storm"
    online_routing: bool = False  # let the routing API drive the time matrix too
    failure_rate: float = 0.05  # chance a customer is absent at a stop
    use_gnn: bool = False
    gnn_epochs: int = 50
    dqn_timesteps: int = 3000
    weight_range_kg: tuple[int, int] = (10, 100)
    # Parcel dimensions (cm); volume is derived from them.
    length_range_cm: tuple[int, int] = (20, 90)
    width_range_cm: tuple[int, int] = (20, 60)
    height_range_cm: tuple[int, int] = (15, 50)
    priority_levels: int = 3
    cost_model: CostModel = field(default_factory=CostModel)
    driver_rules: DriverRules = field(default_factory=DriverRules)


@dataclass
class TruckResult:
    plan: TruckPlan
    packages: int
    peak_load_utilization: float  # heaviest single wave vs capacity
    trip_geometries: dict[int, list[list[float]]] = field(default_factory=dict)
    gnn_suggestion: list[int] | None = None


@dataclass
class FleetResult:
    truck_results: list[TruckResult]
    kpis: dict
    solver: str
    weather: str  # resolved condition (clear|rain|storm)
    weather_source: str  # how it was resolved (live / manual / fallback)
    provider: str
    geometry_provider: str
    generated_at: str

    def to_dict(self) -> dict:
        return asdict(self)


def _resolve_weather(config: PipelineConfig, warehouses: list[Warehouse]) -> tuple[Weather, str]:
    """Turn the requested weather mode into a concrete condition + source label."""
    if config.weather_mode == "live":
        lat = sum(wh.latitude for wh in warehouses) / len(warehouses)
        lon = sum(wh.longitude for wh in warehouses) / len(warehouses)
        return fetch_live_weather(lat, lon)
    return Weather(config.weather_mode), "manual override"


def generate_packages(points: list[DeliveryPoint], config: PipelineConfig) -> list[Package]:
    """Create one randomized package per delivery point (seeded, reproducible)."""
    rng = np.random.default_rng(config.seed)
    packages = []
    for i, point in enumerate(points):
        length = int(rng.integers(*config.length_range_cm))
        width = int(rng.integers(*config.width_range_cm))
        height = int(rng.integers(*config.height_range_cm))
        packages.append(
            Package(
                id=i,
                address=point.address,
                latitude=point.latitude,
                longitude=point.longitude,
                weight_kg=int(rng.integers(*config.weight_range_kg)),
                volume_m3=round(length * width * height / 1_000_000, 3),  # cm³ -> m³
                priority=int(rng.integers(0, config.priority_levels)),
                window=point.window,
                warehouse_id=point.warehouse_id,
                length_cm=length,
                width_cm=width,
                height_cm=height,
            )
        )
    return packages


def _provider_stops(truck: Truck, depot: Warehouse) -> list[Stop]:
    stops = [Stop(index=0, latitude=depot.latitude, longitude=depot.longitude)]
    for offset, package in enumerate(truck.packages, start=1):
        stops.append(
            Stop(
                index=offset,
                latitude=package.latitude,
                longitude=package.longitude,
                package_id=package.id,
                priority=package.priority,
                window=package.window,
            )
        )
    return stops


def _trip_geometry(
    plan: TruckPlan, depot: Warehouse, geometry_provider: GeometryProvider
) -> dict[int, list[list[float]]]:
    """Road path for each trip: depot -> its served/attempted stops -> depot."""
    trips: dict[int, list[tuple[float, float]]] = {}
    for visit in plan.visits:
        if visit.kind in ("delivery", "failed"):
            trips.setdefault(visit.trip_number, []).append((visit.latitude, visit.longitude))
    geometries: dict[int, list[list[float]]] = {}
    depot_point = (depot.latitude, depot.longitude)
    for trip_number, stops in trips.items():
        geometries[trip_number] = geometry_provider.path([depot_point, *stops, depot_point])
    return geometries


def _departure_datetime(base: datetime, minutes: float) -> datetime:
    minutes = max(0.0, min(minutes, 23 * 60 + 59))
    return base.replace(hour=int(minutes // 60), minute=int(minutes % 60), second=0, microsecond=0)


def _time_aware_matrix(
    provider: TravelTimeProvider,
    stops: list[Stop],
    weather_mult: float,
    base_travel: np.ndarray,
    sequenced,
    base_dt: datetime,
) -> np.ndarray:
    """Overlay each trip's travel times, recomputed at the trip's departure.

    A stop belongs to exactly one trip, so the depot/stop legs of each trip can
    be written into a single combined matrix without conflict. Morning trips get
    morning traffic, afternoon trips get afternoon traffic.
    """
    combined = base_travel.copy()
    for wave in sequenced:
        depart = _departure_datetime(base_dt, wave.departure_min)
        sub_stops = [stops[0]] + [stops[n] for n in wave.nodes]
        sub = provider.matrix(sub_stops, depart) * weather_mult
        indices = [0, *wave.nodes]  # local order matches sub's rows/cols
        for a_local, a_global in enumerate(indices):
            for b_local, b_global in enumerate(indices):
                combined[a_global][b_global] = sub[a_local][b_local]
    return combined


def _solve(ctx, package_waves, node_waves, config: PipelineConfig):
    if config.solver == "dqn":
        from .dqn import sequence_waves_with_dqn, train_dqn

        model = train_dqn(ctx, node_waves, timesteps=config.dqn_timesteps, seed=config.seed)
        return chain_departures(ctx, sequence_waves_with_dqn(model, ctx, node_waves))
    return sequence_waves(ctx, package_waves)


def _plan_truck(
    truck: Truck,
    depot: Warehouse,
    provider: TravelTimeProvider,
    geometry_provider: GeometryProvider,
    weather: Weather,
    config: PipelineConfig,
) -> TruckResult:
    stops = _provider_stops(truck, depot)
    base_dt = datetime.now().replace(
        hour=config.driver_rules.shift_start_min // 60, minute=0, second=0, microsecond=0
    )
    travel = provider.matrix(stops, base_dt) * weather.travel_multiplier
    ctx = build_context(depot, truck, truck.packages, travel, config.driver_rules, config.cost_model)

    package_waves = build_waves(truck.packages, truck)
    node_waves = [[ctx.index_of(pkg) for pkg in wave] for wave in package_waves]
    sequenced = _solve(ctx, package_waves, node_waves, config)

    # Second pass: price each trip at its real departure time, then re-plan the
    # sequence against those traffic-accurate times.
    if provider.time_sensitive and sequenced:
        travel = _time_aware_matrix(provider, stops, weather.travel_multiplier, travel, sequenced, base_dt)
        ctx = build_context(
            depot, truck, truck.packages, travel, config.driver_rules, config.cost_model
        )
        if config.solver != "dqn":  # avoid retraining the DQN; reuse its sequence
            sequenced = sequence_waves(ctx, package_waves)

    gnn_suggestion = None
    if config.use_gnn:
        from .gnn import suggest_visit_order

        gnn_suggestion = suggest_visit_order(
            stops, travel, epochs=config.gnn_epochs, seed=config.seed
        )

    rng = np.random.default_rng(config.seed + truck.id)
    plan = execute(ctx, sequenced, rng, failure_rate=config.failure_rate)

    peak_load = max(
        (sum(pkg.weight_kg for pkg in wave) for wave in package_waves), default=0.0
    )
    return TruckResult(
        plan=plan,
        packages=len(truck.packages),
        peak_load_utilization=round(peak_load / truck.capacity_kg, 3),
        trip_geometries=_trip_geometry(plan, depot, geometry_provider),
        gnn_suggestion=gnn_suggestion,
    )


def run_pipeline(
    warehouses: list[Warehouse],
    packages: list[Package],
    trucks: list[Truck],
    provider: TravelTimeProvider | None = None,
    geometry_provider: GeometryProvider | None = None,
    config: PipelineConfig | None = None,
) -> FleetResult:
    config = config or PipelineConfig()
    provider = provider or OfflineEstimator()
    geometry_provider = geometry_provider or StraightLineGeometry()
    warehouses_by_id = {wh.id: wh for wh in warehouses}
    weather, weather_source = _resolve_weather(config, warehouses)

    for truck in trucks:
        truck.packages.clear()
    assign_nearest_warehouse(packages, warehouses)
    unassigned = load_trucks(packages, trucks)

    truck_results: list[TruckResult] = []
    for truck in trucks:
        if not truck.packages:
            truck_results.append(TruckResult(TruckPlan(truck.id, truck.warehouse_id), 0, 0.0))
            continue
        truck_results.append(
            _plan_truck(
                truck,
                warehouses_by_id[truck.warehouse_id],
                provider,
                geometry_provider,
                weather,
                config,
            )
        )

    kpis = _fleet_kpis(truck_results, packages, unassigned, config)
    return FleetResult(
        truck_results=truck_results,
        kpis=kpis,
        solver=config.solver,
        weather=weather.value,
        weather_source=weather_source,
        provider=provider.name,
        geometry_provider=geometry_provider.name,
        generated_at=datetime.now().isoformat(timespec="seconds"),
    )


def _fleet_kpis(
    truck_results: list[TruckResult],
    packages: list[Package],
    unassigned: list[Package],
    config: PipelineConfig,
) -> dict:
    deliveries = [
        v for r in truck_results for v in r.plan.visits if v.kind in ("delivery", "failed")
    ]
    served = [v for v in deliveries if v.kind == "delivery"]
    on_time = sum(1 for v in served if v.on_time)
    active = [r for r in truck_results if r.packages > 0]
    trips = sum(r.plan.trips for r in truck_results)

    breakdown: dict[str, float] = {}
    for r in truck_results:
        for key, value in r.plan.cost_breakdown.items():
            breakdown[key] = round(breakdown.get(key, 0.0) + value, 1)
    # Unassigned packages never reached a truck: cost them here.
    unserved_extra = sum(CostModel.priority_multiplier(p.priority) for p in unassigned)
    if unserved_extra:
        extra = config.cost_model.unserved_penalty * unserved_extra
        breakdown["unserved"] = round(breakdown.get("unserved", 0.0) + extra, 1)
        breakdown["total"] = round(breakdown.get("total", 0.0) + extra, 1)

    return {
        "total_cost": breakdown.get("total", 0.0),
        "cost_breakdown": breakdown,
        "total_packages": len(packages),
        "unassigned_packages": len(unassigned),
        "stops_served": len(served),
        "failed_deliveries": sum(r.plan.failed for r in truck_results),
        "on_time_deliveries": on_time,
        "on_time_rate": round(on_time / len(served), 3) if served else None,
        "total_drive_min": round(sum(r.plan.drive_min for r in truck_results), 1),
        "total_distance_km": round(sum(r.plan.distance_km for r in truck_results), 1),
        "total_waiting_min": round(sum(r.plan.waiting_min for r in truck_results), 1),
        "total_overtime_min": round(sum(r.plan.overtime_min for r in truck_results), 1),
        "total_trips": trips,
        "avg_stops_per_trip": round(len(served) / trips, 1) if trips else 0.0,
        "active_trucks": len(active),
        "idle_trucks": len(truck_results) - len(active),
        "avg_peak_load_utilization": round(
            sum(r.peak_load_utilization for r in active) / len(active), 3
        )
        if active
        else 0.0,
    }
