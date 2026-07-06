from engine.clustering import assign_clusters
from engine.entities import Package, TimeWindow


def make_package(pkg_id: int, lat: float, lon: float) -> Package:
    return Package(
        id=pkg_id,
        address=f"Stop {pkg_id}",
        latitude=lat,
        longitude=lon,
        weight_kg=10,
        volume_m3=1,
        priority=0,
        window=TimeWindow(540, 1080),
    )


def test_every_package_gets_a_cluster():
    # Two dense groups plus one isolated outlier (DBSCAN noise).
    packages = [
        make_package(0, 19.100, 72.850),
        make_package(1, 19.101, 72.851),
        make_package(2, 19.102, 72.852),
        make_package(3, 19.300, 73.100),
        make_package(4, 19.301, 73.101),
        make_package(5, 19.900, 73.900),  # outlier
    ]
    assign_clusters(packages)
    assert all(pkg.cluster is not None and pkg.cluster >= 0 for pkg in packages)


def test_dense_neighbours_share_a_cluster():
    packages = [make_package(i, 19.100 + i * 0.001, 72.850) for i in range(4)]
    assign_clusters(packages)
    assert len({pkg.cluster for pkg in packages}) == 1


def test_empty_input_is_a_noop():
    assign_clusters([])  # must not raise
