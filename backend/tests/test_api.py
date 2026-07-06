import requests

from engine import routing_api


def test_full_api_round_trip(client, monkeypatch):
    # Force external routing to fail so the run stays offline and deterministic;
    # geometry then exercises the straight-line fallback path.
    def offline(*args, **kwargs):
        raise requests.ConnectionError("offline test")

    monkeypatch.setattr(routing_api.requests, "get", offline)

    assert client.get("/api/health").json() == {"status": "ok"}

    warehouses = client.get("/api/warehouses").json()
    trucks = client.get("/api/trucks").json()
    packages = client.get("/api/packages").json()
    assert len(warehouses) == 9
    assert len(trucks) == 9
    assert len(packages) == 93

    response = client.post(
        "/api/optimize",
        json={"solver": "heuristic", "weather_mode": "rain", "online_routing": False},
    )
    assert response.status_code == 202
    assert response.json()["online_routing"] is False
    run_id = response.json()["id"]

    run = client.get(f"/api/runs/{run_id}").json()
    assert run["status"] == "completed", run.get("error")
    assert run["weather"] == "rain"  # manual override resolves to itself
    assert run["kpis"]["stops_served"] > 0
    assert run["kpis"]["cost_breakdown"]["total"] == run["kpis"]["total_cost"]

    routes = client.get(f"/api/runs/{run_id}/routes").json()["routes"]
    assert routes
    kinds = {v["kind"] for route in routes for v in route["visits"]}
    assert "depart" in kinds and "delivery" in kinds
    first_delivery = next(
        v for route in routes for v in route["visits"] if v["kind"] == "delivery"
    )
    assert first_delivery["window"] and first_delivery["departure"]
    # Stops are identified by the company's own order reference / recipient (Stage 2).
    assert first_delivery["reference"] and first_delivery["recipient"]

    # Every active truck carries one geometry polyline per trip (straight-line
    # fallback here), each a list of [lat, lon] points.
    active = next(r for r in routes if r["geometry"])
    assert active["geometry"]
    assert all(len(point) == 2 for polyline in active["geometry"] for point in polyline)


def test_demo_has_a_seeded_route_plan(client):
    # The demo org is pre-loaded with one offline run so its map isn't blank.
    latest = client.get("/api/runs/latest")
    assert latest.status_code == 200
    assert latest.json()["status"] == "completed"
    assert client.get("/api/kpis").json()["kpis"] is not None


def test_truck_crud(client):
    created = client.post(
        "/api/trucks", json={"capacity_kg": 1234, "volume_m3": 99, "warehouse_id": 1}
    )
    assert created.status_code == 201
    truck_id = created.json()["id"]

    updated = client.put(
        f"/api/trucks/{truck_id}", json={"capacity_kg": 1500, "volume_m3": 120, "warehouse_id": 2}
    )
    assert updated.json()["capacity_kg"] == 1500

    assert client.delete(f"/api/trucks/{truck_id}").status_code == 204
    assert client.get(f"/api/trucks/{truck_id}").status_code in (404, 405)


def test_invalid_request_is_rejected(client):
    assert client.post("/api/optimize", json={"solver": "quantum"}).status_code == 422
    assert client.post("/api/optimize", json={"weather_mode": "hail"}).status_code == 422


def test_protected_endpoints_require_auth(anon_client):
    # No session cookie -> the fleet/optimization API is closed.
    assert anon_client.get("/api/warehouses").status_code == 401
    assert anon_client.get("/api/kpis").status_code == 401
    assert anon_client.post("/api/optimize", json={"solver": "heuristic"}).status_code == 401
    # Health stays public for liveness checks.
    assert anon_client.get("/api/health").status_code == 200
