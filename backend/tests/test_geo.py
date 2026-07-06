from engine.geo import haversine_km


def test_zero_distance():
    assert haversine_km(19.0, 72.8, 19.0, 72.8) == 0.0


def test_known_distance_mumbai_to_pune():
    # ~120 km great-circle between Mumbai (19.076, 72.877) and Pune (18.520, 73.856)
    distance = haversine_km(19.076, 72.877, 18.520, 73.856)
    assert 115 <= distance <= 125


def test_symmetry():
    assert haversine_km(19.1, 72.8, 19.2, 73.0) == haversine_km(19.2, 73.0, 19.1, 72.8)
