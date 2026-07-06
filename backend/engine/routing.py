"""Wave-sequencing heuristic: cheapest insertion, 2-opt, departure timing.

This is the primary solver. Sequences are scored with a planning-level cost
(drive + fuel + waiting + priority-weighted lateness); the shared simulator in
:mod:`engine.simulate` later adds breaks, reloads, and failures.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .costs import CostModel
from .drivers import DriverRules
from .entities import Package, Truck, Warehouse
from .geo import ROAD_WINDING_FACTOR, haversine_km


@dataclass
class RoutingContext:
    """Per-truck routing data. Matrix index 0 is the depot; package i is i+1."""

    depot: Warehouse
    truck: Truck
    packages: list[Package]
    travel_min: np.ndarray  # weather-adjusted travel times
    distance_km: np.ndarray
    rules: DriverRules
    cost_model: CostModel

    def index_of(self, package: Package) -> int:
        return self.packages.index(package) + 1

    def window(self, node: int):
        return self.packages[node - 1].window

    def priority(self, node: int) -> int:
        return self.packages[node - 1].priority


@dataclass
class SequencedWave:
    nodes: list[int]  # matrix indices in visit order (no depot)
    departure_min: float = 0.0
    planned_cost: float = 0.0


def build_context(
    depot: Warehouse,
    truck: Truck,
    packages: list[Package],
    travel_min: np.ndarray,
    rules: DriverRules,
    cost_model: CostModel,
) -> RoutingContext:
    points = [(depot.latitude, depot.longitude)] + [(p.latitude, p.longitude) for p in packages]
    n = len(points)
    distance = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            km = haversine_km(*points[i], *points[j]) * ROAD_WINDING_FACTOR
            distance[i][j] = distance[j][i] = km
    return RoutingContext(depot, truck, packages, travel_min, distance, rules, cost_model)


def _arrival_offsets(ctx: RoutingContext, nodes: list[int]) -> list[float]:
    """Minutes from depot departure to arrival at each node (no waiting)."""
    offsets, elapsed, prev = [], 0.0, 0
    for node in nodes:
        elapsed += ctx.travel_min[prev][node]
        offsets.append(elapsed)
        elapsed += ctx.rules.service_time_min
        prev = node
    return offsets


def optimal_departure(ctx: RoutingContext, nodes: list[int], earliest_min: float) -> float:
    """Latest useful departure: nobody waits, nobody is late if avoidable.

    ``d_no_wait`` removes all idling at stops; ``d_latest`` is the last moment
    the whole sequence stays inside its windows. Departing inside
    [earliest, d_latest] as close to d_no_wait as possible batches late-window
    stops (leave at 4 PM, not 9 AM) without creating avoidable lateness.
    """
    offsets = _arrival_offsets(ctx, nodes)
    d_no_wait = max(ctx.window(n).start_min - off for n, off in zip(nodes, offsets))
    d_latest = min(ctx.window(n).end_min - off for n, off in zip(nodes, offsets))
    departure = min(max(d_no_wait, earliest_min), max(d_latest, earliest_min))
    return max(departure, ctx.rules.shift_start_min)


def evaluate(ctx: RoutingContext, nodes: list[int], departure_min: float) -> dict[str, float]:
    """Planning-level forward pass: drive, fuel, waiting, weighted lateness.

    Approximates the lunch break the simulator will insert: taken at the depot
    (absorbed into the pre-departure wait) if departing after the lunch hour,
    otherwise after the first delivery completed past it.
    """
    time = departure_min
    drive = wait = late_weighted = km = 0.0
    prev = 0
    lunch_taken = departure_min >= ctx.rules.lunch_earliest_min
    for node in nodes:
        leg = ctx.travel_min[prev][node]
        drive += leg
        km += ctx.distance_km[prev][node]
        time += leg
        window = ctx.window(node)
        if time < window.start_min:
            wait += window.start_min - time
            time = window.start_min
        elif time > window.end_min:
            late_weighted += (time - window.end_min) * CostModel.priority_multiplier(
                ctx.priority(node)
            )
        time += ctx.rules.service_time_min
        if not lunch_taken and time >= ctx.rules.lunch_earliest_min:
            time += ctx.rules.lunch_duration_min
            lunch_taken = True
        prev = node
    drive += ctx.travel_min[prev][0]  # back to depot
    km += ctx.distance_km[prev][0]
    time += ctx.travel_min[prev][0]

    cm = ctx.cost_model
    cost = (
        cm.drive_weight * drive
        + cm.fuel_weight * km
        + cm.waiting_weight * wait
        + cm.lateness_weight * late_weighted
        + cm.overtime_weight * max(0.0, time - ctx.rules.shift_end_min)
    )
    return {"cost": cost, "end_min": time, "drive_min": drive, "distance_km": km}


def _best_departure(ctx: RoutingContext, nodes: list[int], earliest_min: float) -> float:
    """Window-optimal departure, also trying a lunch-length earlier variant.

    Departing before the lunch hour means the break lands mid-route; leaving
    slightly earlier can absorb it without making anyone late. Evaluate both.
    """
    departure = optimal_departure(ctx, nodes, earliest_min)
    earlier = max(earliest_min, ctx.rules.shift_start_min, departure - ctx.rules.lunch_duration_min)
    candidates = {departure, earlier}
    return min(candidates, key=lambda d: evaluate(ctx, nodes, d)["cost"])


def _wave_cost(
    ctx: RoutingContext, nodes: list[int], earliest_min: float
) -> tuple[float, float, float]:
    """Returns (cost, wave end time, departure used)."""
    if not nodes:
        return 0.0, earliest_min, earliest_min
    departure = _best_departure(ctx, nodes, earliest_min)
    result = evaluate(ctx, nodes, departure)
    waiting_at_depot = departure - earliest_min
    cost = result["cost"] + ctx.cost_model.trip_fixed_cost
    cost += ctx.cost_model.waiting_weight * waiting_at_depot
    return cost, result["end_min"], departure


def _cheapest_insertion(ctx: RoutingContext, nodes: list[int], earliest_min: float) -> list[int]:
    remaining = sorted(nodes, key=lambda n: ctx.window(n).start_min)
    sequence: list[int] = [remaining.pop(0)]
    while remaining:
        best = None
        for node in remaining:
            for pos in range(len(sequence) + 1):
                candidate = sequence[:pos] + [node] + sequence[pos:]
                cost, _, _ = _wave_cost(ctx, candidate, earliest_min)
                if best is None or cost < best[0]:
                    best = (cost, node, pos)
        _, node, pos = best
        sequence.insert(pos, node)
        remaining.remove(node)
    return sequence


def _local_search(ctx: RoutingContext, nodes: list[int], earliest_min: float) -> list[int]:
    """Improve a sequence with 2-opt and or-opt until neither helps.

    2-opt reverses a segment (untangles crossings); or-opt lifts a short run of
    1-3 stops and reinserts it elsewhere. Or-opt is what pulls a stop that's
    physically on the way — but stranded out of order by the initial insertion —
    back into its natural position, instead of leaving it for a later detour.
    """
    best = nodes[:]
    best_cost, _, _ = _wave_cost(ctx, best, earliest_min)
    improved = True
    while improved:
        improved = False

        # 2-opt: reverse best[i:j+1].
        for i in range(len(best) - 1):
            for j in range(i + 1, len(best)):
                candidate = best[:i] + best[i : j + 1][::-1] + best[j + 1 :]
                cost, _, _ = _wave_cost(ctx, candidate, earliest_min)
                if cost < best_cost - 1e-9:
                    best, best_cost, improved = candidate, cost, True

        # Or-opt: move a segment of length 1..3 to a different position.
        for seg_len in (1, 2, 3):
            for i in range(len(best) - seg_len + 1):
                segment = best[i : i + seg_len]
                rest = best[:i] + best[i + seg_len :]
                for pos in range(len(rest) + 1):
                    if pos == i:
                        continue  # same location
                    candidate = rest[:pos] + segment + rest[pos:]
                    cost, _, _ = _wave_cost(ctx, candidate, earliest_min)
                    if cost < best_cost - 1e-9:
                        best, best_cost, improved = candidate, cost, True
    return best


def sequence_waves(ctx: RoutingContext, waves: list[list[Package]]) -> list[SequencedWave]:
    """Sequence every wave, chain departures, and try inter-wave relocations."""
    node_waves = [[ctx.index_of(pkg) for pkg in wave] for wave in waves]

    def solve_all(node_waves: list[list[int]]) -> tuple[list[SequencedWave], float]:
        planned: list[SequencedWave] = []
        earliest = float(ctx.rules.shift_start_min)
        total = 0.0
        for nodes in node_waves:
            if not nodes:
                continue
            seq = _local_search(ctx, _cheapest_insertion(ctx, nodes, earliest), earliest)
            cost, end, departure = _wave_cost(ctx, seq, earliest)
            planned.append(SequencedWave(seq, departure, round(cost, 1)))
            earliest = end + ctx.rules.reload_time_min
            total += cost
        return planned, total

    planned, base_cost = solve_all(node_waves)
    if len(node_waves) > 1:
        # One relocation pass: moving a stop to the neighbouring wave sometimes
        # pays for itself (fewer km now, better window fit later).
        for w, nodes in enumerate(node_waves):
            for node in nodes[:]:
                for target in (w - 1, w + 1):
                    if not 0 <= target < len(node_waves):
                        continue
                    trial = [list(x) for x in node_waves]
                    trial[w].remove(node)
                    trial[target].append(node)
                    if not _fits(ctx, trial[target]):
                        continue
                    candidate, cost = solve_all(trial)
                    if cost < base_cost - 1e-9:
                        node_waves, planned, base_cost = trial, candidate, cost
                        break
    return planned


def _fits(ctx: RoutingContext, nodes: list[int]) -> bool:
    weight = sum(ctx.packages[n - 1].weight_kg for n in nodes)
    volume = sum(ctx.packages[n - 1].volume_m3 for n in nodes)
    return weight <= ctx.truck.capacity_kg and volume <= ctx.truck.volume_m3


def chain_departures(ctx: RoutingContext, node_seqs: list[list[int]]) -> list[SequencedWave]:
    """Attach optimized departure times to externally sequenced waves (e.g. DQN)."""
    planned: list[SequencedWave] = []
    earliest = float(ctx.rules.shift_start_min)
    for seq in node_seqs:
        if not seq:
            continue
        cost, end, departure = _wave_cost(ctx, seq, earliest)
        planned.append(SequencedWave(seq, departure, round(cost, 1)))
        earliest = end + ctx.rules.reload_time_min
    return planned
