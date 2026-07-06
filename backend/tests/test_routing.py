import itertools

import numpy as np

from engine.costs import CostModel
from engine.drivers import DriverRules
from engine.entities import TimeWindow
from engine.geo import haversine_km
from engine.routing import _wave_cost, build_context, evaluate, optimal_departure, sequence_waves
from engine.waves import build_waves

from .helpers import DEPOT, make_context, make_package, make_truck


def _distance_context(packages):
    """A context whose travel times track real distances (minutes ~= km)."""
    points = [(DEPOT.latitude, DEPOT.longitude)] + [(p.latitude, p.longitude) for p in packages]
    n = len(points)
    travel = np.array([[haversine_km(*points[i], *points[j]) for j in range(n)] for i in range(n)])
    return build_context(DEPOT, make_truck(), packages, travel, DriverRules(), CostModel())


def test_departure_removes_waiting_for_late_windows():
    # One stop, 10 minutes away, window 3-5 PM: leave at 2:50 PM, not 9 AM.
    packages = [make_package(0, TimeWindow(15 * 60, 17 * 60))]
    ctx = make_context(packages, minutes_apart=10.0)
    departure = optimal_departure(ctx, [1], earliest_min=540)
    assert departure == 15 * 60 - 10


def test_departure_never_before_earliest():
    packages = [make_package(0, TimeWindow(540, 600))]
    ctx = make_context(packages, minutes_apart=10.0)
    assert optimal_departure(ctx, [1], earliest_min=700) == 700


def test_evaluate_counts_weighted_lateness():
    packages = [make_package(0, TimeWindow(540, 560), priority=2)]
    ctx = make_context(packages, minutes_apart=30.0)
    result = evaluate(ctx, [1], departure_min=540)  # arrives 570, 10 min late, x4
    late_cost = ctx.cost_model.lateness_weight * 10 * 4
    assert result["cost"] >= late_cost


def test_sequencing_orders_by_window_feasibility():
    # A morning-only stop and an evening-only stop: served in that order in
    # one trip, both feasible.
    packages = [
        make_package(0, TimeWindow(16 * 60, 18 * 60)),
        make_package(1, TimeWindow(9 * 60, 10 * 60)),
    ]
    ctx = make_context(packages, minutes_apart=10.0)
    sequenced = sequence_waves(ctx, build_waves(packages, ctx.truck))
    order = [node for wave in sequenced for node in wave.nodes]
    assert order.index(2) < order.index(1)  # morning stop (node 2) first


def test_solver_finds_near_optimal_route():
    """The local search (2-opt + or-opt) should find essentially the optimal
    tour for a small stop set — which means it never leaves an on-the-way stop
    to be picked up by a wasteful detour. Compared against brute force."""
    coords = [(19.03, 72.82), (19.05, 72.85), (19.02, 72.88), (19.07, 72.83), (19.04, 72.90)]
    packages = [make_package(i, TimeWindow(540, 1080), lat=lat, lon=lon) for i, (lat, lon) in enumerate(coords)]
    ctx = _distance_context(packages)
    nodes = [ctx.index_of(p) for p in packages]

    optimal = min(_wave_cost(ctx, list(perm), 540.0)[0] for perm in itertools.permutations(nodes))
    sequenced = sequence_waves(ctx, [packages])
    solved = _wave_cost(ctx, sequenced[0].nodes, 540.0)[0]

    assert solved <= optimal * 1.02  # within 2% of the true optimum
