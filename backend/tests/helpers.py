"""Shared builders for engine tests."""

from __future__ import annotations

import numpy as np

from engine.costs import CostModel
from engine.drivers import DriverRules
from engine.entities import Package, TimeWindow, Truck, Warehouse
from engine.routing import RoutingContext, build_context

DEPOT = Warehouse(1, "Test Depot", 19.00, 72.80)


def make_package(
    pkg_id: int,
    window: TimeWindow,
    lat: float = 19.05,
    lon: float = 72.85,
    weight: float = 50,
    volume: float = 0.2,
    priority: int = 0,
) -> Package:
    return Package(
        id=pkg_id,
        address=f"Stop {pkg_id}",
        latitude=lat,
        longitude=lon,
        weight_kg=weight,
        volume_m3=volume,
        priority=priority,
        window=window,
        warehouse_id=DEPOT.id,
    )


def make_truck(capacity: float = 1000, volume: float = 10) -> Truck:
    return Truck(1, capacity, volume, DEPOT.id, DEPOT.latitude, DEPOT.longitude)


def make_context(
    packages: list[Package],
    minutes_apart: float = 10.0,
    truck: Truck | None = None,
    rules: DriverRules | None = None,
) -> RoutingContext:
    """Context where every pair of points is `minutes_apart` minutes apart."""
    n = len(packages) + 1
    travel = np.full((n, n), minutes_apart)
    np.fill_diagonal(travel, 0.0)
    return build_context(
        DEPOT, truck or make_truck(), packages, travel, rules or DriverRules(), CostModel()
    )
