from engine.costs import CostModel


def test_priority_multiplier_doubles_per_level():
    assert CostModel.priority_multiplier(0) == 1
    assert CostModel.priority_multiplier(1) == 2
    assert CostModel.priority_multiplier(2) == 4


def test_breakdown_totals_components():
    model = CostModel()
    breakdown = model.breakdown(
        drive_min=100,
        distance_km=50,
        departures=2,
        waiting_min=30,
        weighted_lateness_min=10,
        overtime_min=5,
        weighted_unserved=1,
    )
    assert breakdown["drive"] == 100.0
    assert breakdown["fuel"] == 100.0
    assert breakdown["trips"] == 60.0
    assert breakdown["waiting"] == 6.0
    assert breakdown["lateness"] == 30.0
    assert breakdown["overtime"] == 25.0
    assert breakdown["unserved"] == 500.0
    assert breakdown["total"] == 821.0


def test_lateness_scales_with_priority():
    model = CostModel()
    assert model.lateness_cost(10, priority=2) == 4 * model.lateness_cost(10, priority=0)
