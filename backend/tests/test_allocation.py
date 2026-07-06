from engine.allocation import assign_nearest_warehouse, load_trucks
from engine.entities import Package, TimeWindow, Truck, Warehouse

WAREHOUSES = [
    Warehouse(1, "North", 19.20, 72.90),
    Warehouse(2, "South", 19.00, 72.80),
]


def make_package(pkg_id: int, lat: float, lon: float, weight: float = 10, volume: float = 1) -> Package:
    return Package(
        id=pkg_id,
        address=f"Stop {pkg_id}",
        latitude=lat,
        longitude=lon,
        weight_kg=weight,
        volume_m3=volume,
        priority=0,
        window=TimeWindow(540, 1080),
    )


def make_truck(truck_id: int, warehouse_id: int, capacity: float = 1000, volume: float = 100) -> Truck:
    depot = next(wh for wh in WAREHOUSES if wh.id == warehouse_id)
    return Truck(truck_id, capacity, volume, warehouse_id, depot.latitude, depot.longitude)


def test_packages_go_to_nearest_warehouse():
    near_north = make_package(0, 19.21, 72.91)
    near_south = make_package(1, 18.99, 72.79)
    assign_nearest_warehouse([near_north, near_south], WAREHOUSES)
    assert near_north.warehouse_id == 1
    assert near_south.warehouse_id == 2


def test_daily_budget_limits_are_respected():
    # Daily budget = capacity x 2 (one reload). 4 x 60 kg > 200 kg budget.
    packages = [make_package(i, 19.20, 72.90, weight=60) for i in range(4)]
    for pkg in packages:
        pkg.warehouse_id = 1
    truck = make_truck(1, 1, capacity=100)
    unassigned = load_trucks(packages, [truck], max_daily_loads=2)
    assert truck.used_capacity_kg <= truck.capacity_kg * 2
    assert len(truck.packages) + len(unassigned) == 4
    assert unassigned  # the fourth package exceeds the daily budget


def test_overflow_spills_to_sibling_truck():
    packages = [make_package(i, 19.20 + i * 0.001, 72.90, weight=80) for i in range(4)]
    for pkg in packages:
        pkg.warehouse_id = 1
    small = make_truck(1, 1, capacity=100)
    big = make_truck(2, 1, capacity=500)
    unassigned = load_trucks(packages, [small, big])
    assert not unassigned
    assert len(small.packages) + len(big.packages) == 4


def test_warehouse_without_trucks_reports_unassigned():
    package = make_package(0, 19.20, 72.90)
    package.warehouse_id = 1
    unassigned = load_trucks([package], [make_truck(1, 2)])
    assert unassigned == [package]


# --- Hybrid assignment + physical parcel fit (Stage 2) ----------------------


def test_explicit_warehouse_is_honored():
    # Sits right next to North(1) but the company explicitly ships from South(2).
    explicit = make_package(0, 19.21, 72.91)
    explicit.warehouse_id = 2
    auto = make_package(1, 19.21, 72.91)  # no source -> nearest (North)
    assign_nearest_warehouse([explicit, auto], WAREHOUSES)
    assert explicit.warehouse_id == 2  # honored, not overwritten
    assert auto.warehouse_id == 1  # nearest


def _sized_truck(length, width, height):
    return Truck(
        1, 1000, 9, 1, WAREHOUSES[0].latitude, WAREHOUSES[0].longitude,
        length_cm=length, width_cm=width, height_cm=height,
    )


def _sized_package(pid, length, width, height):
    pkg = make_package(pid, 19.20, 72.90, volume=length * width * height / 1_000_000)
    pkg.warehouse_id = 1
    pkg.length_cm, pkg.width_cm, pkg.height_cm = length, width, height
    return pkg


def test_oversized_parcel_cannot_be_loaded():
    truck = _sized_truck(300, 200, 150)
    fits = _sized_package(0, 120, 80, 60)
    too_long = _sized_package(1, 320, 40, 30)  # 320 > 300 bay
    assert truck.fits_dimensions(fits) is True
    assert truck.fits_dimensions(too_long) is False

    unassigned = load_trucks([fits, too_long], [truck])
    assert too_long in unassigned
    assert fits in truck.packages


def test_fit_check_allows_rotation():
    truck = _sized_truck(300, 200, 150)
    rotatable = _sized_package(0, 280, 190, 100)  # 190 <= 200 side after rotation
    assert truck.fits_dimensions(rotatable) is True


def test_unknown_dimensions_do_not_gate():
    truck = make_truck(1, 1)  # no bay dimensions
    parcel = _sized_package(0, 999, 999, 999)
    assert truck.fits_dimensions(parcel) is True
