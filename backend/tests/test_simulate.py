import numpy as np

from engine.entities import TimeWindow
from engine.routing import SequencedWave
from engine.simulate import execute

from .helpers import make_context, make_package

RNG = lambda: np.random.default_rng(0)  # noqa: E731

ALL_DAY = TimeWindow(540, 1080)


def test_lunch_break_taken_once_after_one_pm():
    # Stops spaced so the route crosses 1 PM mid-wave.
    packages = [make_package(i, ALL_DAY) for i in range(6)]
    ctx = make_context(packages, minutes_apart=50.0)
    waves = [SequencedWave(nodes=list(range(1, 7)), departure_min=540)]
    plan = execute(ctx, waves, RNG(), failure_rate=0.0)

    breaks = [v for v in plan.visits if v.kind == "break"]
    assert len(breaks) == 1
    assert breaks[0].eta_min >= ctx.rules.lunch_earliest_min
    assert breaks[0].departure_min - breaks[0].eta_min == ctx.rules.lunch_duration_min


def test_reload_between_waves_and_trip_count():
    packages = [make_package(i, ALL_DAY) for i in range(4)]
    ctx = make_context(packages, minutes_apart=5.0)
    waves = [
        SequencedWave(nodes=[1, 2], departure_min=540),
        SequencedWave(nodes=[3, 4], departure_min=700),
    ]
    plan = execute(ctx, waves, RNG(), failure_rate=0.0)
    assert plan.trips == 2
    assert sum(1 for v in plan.visits if v.kind == "reload") == 1
    assert sum(1 for v in plan.visits if v.kind == "depart") == 2


def test_failed_delivery_is_retried_and_can_succeed():
    packages = [make_package(i, ALL_DAY) for i in range(3)]
    ctx = make_context(packages, minutes_apart=5.0)
    waves = [SequencedWave(nodes=[1, 2, 3], departure_min=540)]
    # failure_rate=1 on the first pass would fail the retry too; use a rigged
    # generator: fail exactly the first draw, succeed afterwards.
    draws = iter([0.0, 0.9, 0.9, 0.9, 0.9, 0.9])

    class Rigged:
        def random(self):
            return next(draws)

    plan = execute(ctx, waves, Rigged(), failure_rate=0.05)
    assert sum(1 for v in plan.visits if v.kind == "failed") == 1
    assert plan.stops_served == 3  # all three delivered in the end
    assert plan.failed == 0
    assert plan.trips == 2  # original wave + retry wave


def test_overtime_counted_past_shift_end():
    packages = [make_package(i, ALL_DAY) for i in range(3)]
    ctx = make_context(packages, minutes_apart=60.0)
    waves = [SequencedWave(nodes=[1, 2, 3], departure_min=16 * 60)]
    plan = execute(ctx, waves, RNG(), failure_rate=0.0)
    assert plan.overtime_min > 0
    assert plan.cost_breakdown["overtime"] > 0


def test_first_dispatch_idle_time_is_free():
    packages = [make_package(0, TimeWindow(16 * 60, 17 * 60))]
    ctx = make_context(packages, minutes_apart=10.0)
    waves = [SequencedWave(nodes=[1], departure_min=950)]
    plan = execute(ctx, waves, RNG(), failure_rate=0.0)
    assert plan.waiting_min == 0  # driver is dispatched at 3:50 PM, not paid to idle from 9 AM
