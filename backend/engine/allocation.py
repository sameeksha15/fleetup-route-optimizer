"""Warehouse assignment and capacity-aware truck loading."""

from __future__ import annotations

from collections import defaultdict

from .clustering import assign_clusters
from .entities import Package, Truck, Warehouse
from .geo import haversine_km


def assign_nearest_warehouse(packages: list[Package], warehouses: list[Warehouse]) -> None:
    """Fill in the source warehouse for orders that don't name one.

    Hybrid assignment: an order that already specifies its warehouse (because the
    company knows which depot holds the stock) is left untouched; only the blanks
    are auto-assigned to the geographically closest warehouse.
    """
    if not warehouses:
        return
    for package in packages:
        if package.warehouse_id is not None:
            continue
        nearest = min(
            warehouses,
            key=lambda wh: haversine_km(package.latitude, package.longitude, wh.latitude, wh.longitude),
        )
        package.warehouse_id = nearest.id


def load_trucks(
    packages: list[Package], trucks: list[Truck], max_daily_loads: int = 2
) -> list[Package]:
    """Cluster packages per warehouse and assign them to that warehouse's trucks.

    Within a warehouse, clusters are mapped to trucks round-robin; a package
    that doesn't fit its cluster's truck falls back to the truck with the most
    remaining capacity. A truck's daily budget is ``capacity x max_daily_loads``
    because it can reload at the depot between trips; single-trip limits are
    enforced later by wave planning. Returns packages that fit on no truck.
    """
    trucks_by_warehouse: dict[int, list[Truck]] = defaultdict(list)
    for truck in trucks:
        trucks_by_warehouse[truck.warehouse_id].append(truck)

    packages_by_warehouse: dict[int, list[Package]] = defaultdict(list)
    for package in packages:
        packages_by_warehouse[package.warehouse_id].append(package)

    def try_assign(truck: Truck, package: Package) -> bool:
        fits = (
            truck.used_capacity_kg + package.weight_kg <= truck.capacity_kg * max_daily_loads
            and truck.used_volume_m3 + package.volume_m3 <= truck.volume_m3 * max_daily_loads
            and truck.fits_dimensions(package)  # reject a parcel too large for the bay
        )
        if fits:
            truck.packages.append(package)
        return fits

    unassigned: list[Package] = []
    for warehouse_id, group in packages_by_warehouse.items():
        local_trucks = trucks_by_warehouse.get(warehouse_id)
        if not local_trucks:
            unassigned.extend(group)
            continue

        assign_clusters(group)
        # High-priority, heavy packages claim space first.
        group.sort(key=lambda p: (p.priority, p.weight_kg), reverse=True)

        cluster_ids = sorted({p.cluster for p in group})
        cluster_to_truck = {
            cluster: local_trucks[i % len(local_trucks)] for i, cluster in enumerate(cluster_ids)
        }
        for package in group:
            if try_assign(cluster_to_truck[package.cluster], package):
                continue
            candidates = sorted(local_trucks, key=lambda t: t.remaining_capacity_kg, reverse=True)
            if not any(try_assign(truck, package) for truck in candidates):
                unassigned.append(package)
    return unassigned
