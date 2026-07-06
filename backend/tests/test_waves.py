import numpy as np

from engine.entities import TimeWindow
from engine.routing import sequence_waves
from engine.simulate import execute
from engine.waves import build_waves

from .helpers import make_context, make_package, make_truck


def test_capacity_forces_a_second_wave():
    truck = make_truck(capacity=100)
    packages = [make_package(i, TimeWindow(540, 1080), weight=60) for i in range(3)]
    waves = build_waves(packages, truck)
    assert len(waves) == 3  # 60 kg each, only one fits per 100 kg load


def test_everything_fits_in_one_wave_when_it_can():
    truck = make_truck(capacity=1000)
    packages = [make_package(i, TimeWindow(540 + i * 60, 1080)) for i in range(5)]
    assert len(build_waves(packages, truck)) == 1


def test_no_split_by_time_window_alone():
    """A morning-only and an afternoon-only stop that fit one load stay on the
    same trip — the truck does not make a wasteful second trip just because one
    window opens later. Route timing handles the wait."""
    truck = make_truck(capacity=1000)
    packages = [
        make_package(0, TimeWindow(9 * 60, 11 * 60)),
        make_package(1, TimeWindow(16 * 60, 18 * 60)),
    ]
    assert len(build_waves(packages, truck)) == 1


def test_capacity_split_is_geographic():
    """When capacity forces two trips, each load is a coherent geographic
    sector (not a time-ordered mix), so a truck isn't sent across town twice."""
    truck = make_truck(capacity=130)  # holds two 60 kg packages per load
    north = [
        make_package(0, TimeWindow(540, 1080), lat=19.05, lon=72.85, weight=60),
        make_package(1, TimeWindow(540, 1080), lat=19.06, lon=72.86, weight=60),
    ]
    south = [
        make_package(2, TimeWindow(540, 1080), lat=18.95, lon=72.75, weight=60),
        make_package(3, TimeWindow(540, 1080), lat=18.94, lon=72.74, weight=60),
    ]
    waves = build_waves(north + south, truck)
    assert len(waves) == 2
    # Depot is at lat 19.00: each wave sits entirely on one side of it.
    for wave in waves:
        lats = [p.latitude for p in wave]
        assert all(lat > 19.0 for lat in lats) or all(lat < 19.0 for lat in lats)


def test_late_window_batching_departs_around_four_pm():
    """The user's scenario: a 2-6 PM stop and a 4-6 PM stop in the same area
    should be served in ONE trip that leaves the depot around 4 PM — not a
    9 AM departure with hours of idling, and not two separate trips."""
    packages = [
        make_package(0, TimeWindow(14 * 60, 18 * 60), lat=19.05, lon=72.85),
        make_package(1, TimeWindow(16 * 60, 18 * 60), lat=19.06, lon=72.86),
    ]
    ctx = make_context(packages, minutes_apart=10.0)
    waves = build_waves(packages, ctx.truck)
    assert len(waves) == 1

    sequenced = sequence_waves(ctx, waves)
    assert len(sequenced) == 1
    departure = sequenced[0].departure_min
    # Late enough to batch the 4 PM window without waiting, with at most the
    # two 10-minute legs of slack; never a morning departure.
    assert 15 * 60 <= departure <= 16 * 60

    plan = execute(ctx, sequenced, np.random.default_rng(0), failure_rate=0.0)
    deliveries = [v for v in plan.visits if v.kind == "delivery"]
    assert len(deliveries) == 2
    assert all(v.on_time for v in deliveries)
    assert plan.trips == 1
