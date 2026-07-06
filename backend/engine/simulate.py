"""Execute a planned schedule minute-by-minute.

Both solvers produce sequenced waves; this simulator is the single source of
truth for what actually happens: waiting, service times, the driver's lunch
break, reloads between waves, random failed deliveries (with one retry wave),
overtime, and the final cost breakdown. Sharing it keeps solver comparisons
fair.
"""

from __future__ import annotations

import numpy as np

from .costs import CostModel
from .entities import TimeWindow, TruckPlan, Visit
from .routing import RoutingContext, SequencedWave, optimal_departure


class _Run:
    """Mutable state while walking the schedule."""

    def __init__(self, ctx: RoutingContext, start_min: float):
        self.ctx = ctx
        self.time = start_min
        self.node = 0  # depot
        self.trip = 0
        self.lunch_taken = False
        self.visits: list[Visit] = []
        self.drive_min = 0.0
        self.distance_km = 0.0
        self.waiting_min = 0.0
        self.late_weighted = 0.0
        self.served = 0
        self.failed_pkgs: list[int] = []  # node indices that failed once

    def coords(self, node: int) -> tuple[float, float]:
        if node == 0:
            return self.ctx.depot.latitude, self.ctx.depot.longitude
        pkg = self.ctx.packages[node - 1]
        return pkg.latitude, pkg.longitude

    def record(self, kind: str, node: int, eta: float, departure: float,
               window: TimeWindow | None = None, on_time: bool | None = None) -> None:
        lat, lon = self.coords(node)
        package_id = None if node == 0 else self.ctx.packages[node - 1].id
        if kind in ("depart", "reload", "break", "return"):
            package_id = None
        self.visits.append(
            Visit(kind, self.trip, package_id, lat, lon, round(eta, 1), round(departure, 1),
                  window, on_time)
        )

    def drive_to(self, node: int) -> None:
        self.drive_min += self.ctx.travel_min[self.node][node]
        self.distance_km += self.ctx.distance_km[self.node][node]
        self.time += self.ctx.travel_min[self.node][node]
        self.node = node

    def maybe_lunch(self) -> None:
        if not self.lunch_taken and self.time >= self.ctx.rules.lunch_earliest_min:
            start = self.time
            self.time += self.ctx.rules.lunch_duration_min
            self.lunch_taken = True
            self.record("break", self.node, start, self.time)


def execute(
    ctx: RoutingContext,
    waves: list[SequencedWave],
    rng: np.random.Generator,
    failure_rate: float = 0.0,
) -> TruckPlan:
    rules = ctx.rules
    run = _Run(ctx, rules.shift_start_min)

    def wait_at_depot(until: float) -> None:
        """Idle at the depot; a due lunch break is absorbed into the wait."""
        if until <= run.time:
            return
        wait = until - run.time
        if run.trip == 0:
            wait = 0.0  # the driver is dispatched at the first departure
        elif not run.lunch_taken and until >= rules.lunch_earliest_min + rules.lunch_duration_min:
            start = max(run.time, float(rules.lunch_earliest_min))
            if until - start >= rules.lunch_duration_min:
                run.record("break", 0, start, start + rules.lunch_duration_min)
                run.lunch_taken = True
                wait -= rules.lunch_duration_min
        run.waiting_min += max(wait, 0.0)
        run.time = until

    def serve_wave(nodes: list[int], departure: float) -> None:
        wait_at_depot(departure)
        run.trip += 1
        run.record("depart", 0, run.time, run.time)
        for node in nodes:
            run.drive_to(node)
            arrival = run.time
            window = ctx.window(node)
            if arrival < window.start_min:
                run.waiting_min += window.start_min - arrival
                run.time = window.start_min
            failed = failure_rate > 0 and rng.random() < failure_rate
            if failed:
                run.time += rules.failed_service_min
                run.failed_pkgs.append(node)
                run.record("failed", node, arrival, run.time, window, False)
            else:
                late = run.time > window.end_min
                if late:
                    run.late_weighted += (run.time - window.end_min) * CostModel.priority_multiplier(
                        ctx.priority(node)
                    )
                run.time += rules.service_time_min
                run.served += 1
                run.record("delivery", node, arrival, run.time, window, not late)
            run.maybe_lunch()  # break comes after finishing the stop, not before
        run.drive_to(0)

    pending = [w for w in waves if w.nodes]
    for i, wave in enumerate(pending):
        serve_wave(wave.nodes, wave.departure_min)
        is_last = i == len(pending) - 1
        if not is_last:
            run.maybe_lunch()
            reload_start = run.time
            run.time += rules.reload_time_min
            run.record("reload", 0, reload_start, run.time)

    # One retry wave for customers who were absent — but only where a late
    # redelivery still beats writing the package off as unserved.
    unserved_weighted = 0.0
    if run.failed_pkgs and run.time + rules.reload_time_min < rules.shift_end_min:
        cm = ctx.cost_model

        def worth_retrying(node: int) -> bool:
            eta = run.time + rules.reload_time_min + ctx.travel_min[0][node]
            est_late = max(0.0, eta - ctx.window(node).end_min)
            return cm.lateness_weight * est_late < cm.unserved_penalty

        retry_nodes = sorted(
            (n for n in run.failed_pkgs if worth_retrying(n)),
            key=lambda n: ctx.window(n).end_min,
        )
        if retry_nodes:
            run.failed_pkgs = [n for n in run.failed_pkgs if n not in retry_nodes]
            reload_start = run.time
            run.time += rules.reload_time_min
            run.record("reload", 0, reload_start, run.time)
            departure = optimal_departure(ctx, retry_nodes, run.time)
            serve_wave(retry_nodes, departure)  # second failure here is final

    for node in run.failed_pkgs:
        unserved_weighted += CostModel.priority_multiplier(ctx.priority(node))
    run.record("return", 0, run.time, run.time)

    overtime = max(0.0, run.time - rules.shift_end_min)
    breakdown = ctx.cost_model.breakdown(
        drive_min=run.drive_min,
        distance_km=run.distance_km,
        departures=run.trip,
        waiting_min=run.waiting_min,
        weighted_lateness_min=run.late_weighted,
        overtime_min=overtime,
        weighted_unserved=unserved_weighted,
    )
    return TruckPlan(
        truck_id=ctx.truck.id,
        warehouse_id=ctx.truck.warehouse_id,
        visits=run.visits,
        drive_min=round(run.drive_min, 1),
        distance_km=round(run.distance_km, 1),
        waiting_min=round(run.waiting_min, 1),
        overtime_min=round(overtime, 1),
        stops_served=run.served,
        failed=len(run.failed_pkgs),
        trips=run.trip,
        cost_breakdown=breakdown,
    )
