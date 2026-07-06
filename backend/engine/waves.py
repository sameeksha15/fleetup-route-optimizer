"""Partition a truck's packages into reload waves (physical trips).

A wave is one load: everything in it is carried together, so a wave must fit the
truck's weight and volume limits. The guiding principle is that a truck should
make as few depot returns as possible — it returns only to reload when a single
load cannot carry everything, never merely because some deliveries are due later
in the day. Time windows are handled downstream by route sequencing and
departure timing (the truck waits when it arrives early), so nearby stops with
different windows stay on the same trip and get served on the way instead of
triggering a wasteful second trip.

When a split is unavoidable (total load exceeds capacity), packages are grouped
into geographically coherent sectors by sweeping angularly around the depot, so
each load covers one wedge of the map rather than a scattered set of stops.
"""

from __future__ import annotations

import math

from .entities import Package, Truck


def _fits_one_load(packages: list[Package], truck: Truck) -> bool:
    return (
        sum(p.weight_kg for p in packages) <= truck.capacity_kg
        and sum(p.volume_m3 for p in packages) <= truck.volume_m3
    )


def _sweep_sectors(packages: list[Package], truck: Truck) -> list[list[Package]]:
    """Group packages into capacity-feasible sectors by angle around the depot.

    The classic sweep heuristic: order stops by bearing from the depot, then cut
    the sweep into loads whenever the next stop would overflow capacity. Each
    resulting load is a contiguous angular wedge, keeping it geographically tight.
    """
    ordered = sorted(
        packages,
        key=lambda p: math.atan2(p.latitude - truck.latitude, p.longitude - truck.longitude),
    )
    waves: list[list[Package]] = []
    current: list[Package] = []
    load_kg = load_m3 = 0.0
    for package in ordered:
        fits = (
            load_kg + package.weight_kg <= truck.capacity_kg
            and load_m3 + package.volume_m3 <= truck.volume_m3
        )
        if current and not fits:
            waves.append(current)
            current, load_kg, load_m3 = [], 0.0, 0.0
        current.append(package)
        load_kg += package.weight_kg
        load_m3 += package.volume_m3
    if current:
        waves.append(current)
    return waves


def build_waves(packages: list[Package], truck: Truck) -> list[list[Package]]:
    """Return the reload waves (trips) for one truck's packages."""
    if not packages:
        return []
    if _fits_one_load(packages, truck):
        return [list(packages)]  # a single trip serves everything on the way
    return _sweep_sectors(packages, truck)
