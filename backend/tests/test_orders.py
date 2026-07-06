"""API: per-organization warehouse / order CRUD and org settings (Stage 2)."""


def test_warehouse_crud_and_delete_guard(client):
    created = client.post(
        "/api/warehouses", json={"name": "New Depot", "latitude": 19.1, "longitude": 72.9}
    )
    assert created.status_code == 201, created.text
    wh_id = created.json()["id"]

    updated = client.put(
        f"/api/warehouses/{wh_id}",
        json={"name": "Renamed Depot", "latitude": 19.15, "longitude": 72.95},
    )
    assert updated.json()["name"] == "Renamed Depot"

    # A depot with a vehicle parked at it cannot be deleted.
    truck = client.post(
        "/api/trucks", json={"capacity_kg": 800, "volume_m3": 8, "warehouse_id": wh_id}
    )
    assert truck.status_code == 201
    blocked = client.delete(f"/api/warehouses/{wh_id}")
    assert blocked.status_code == 409

    assert client.delete(f"/api/trucks/{truck.json()['id']}").status_code == 204
    assert client.delete(f"/api/warehouses/{wh_id}").status_code == 204


def test_order_default_window_and_dimensions(client):
    # Omit the window -> inherit the org's working hours (09:00-18:00 by default).
    resp = client.post(
        "/api/orders",
        json={
            "reference": "PO-1",
            "recipient": "Acme Retail",
            "address": "Somewhere",
            "latitude": 19.07,
            "longitude": 72.88,
            "weight_kg": 12,
            "length_cm": 50,
            "width_cm": 40,
            "height_cm": 30,
            "priority": 2,
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["window_start_min"] == 540 and body["window_end_min"] == 1080
    # Volume derived from dimensions: 50*40*30 cm^3 = 0.06 m^3.
    assert abs(body["volume_m3"] - 0.06) < 1e-6

    order_id = body["id"]
    assert client.get(f"/api/orders/{order_id}").json()["reference"] == "PO-1"
    assert client.delete(f"/api/orders/{order_id}").status_code == 204


def test_order_requires_volume_or_dimensions(client):
    resp = client.post(
        "/api/orders",
        json={"address": "x", "latitude": 19.0, "longitude": 72.8, "weight_kg": 5},
    )
    assert resp.status_code == 422  # neither volume nor dimensions given


def test_order_rejects_foreign_warehouse(client):
    resp = client.post(
        "/api/orders",
        json={
            "address": "x", "latitude": 19.0, "longitude": 72.8, "weight_kg": 5,
            "volume_m3": 0.1, "warehouse_id": 999999,
        },
    )
    assert resp.status_code == 422


def test_org_settings_roundtrip(client):
    got = client.get("/api/org/settings").json()
    assert got["working_hours_start_min"] == 540

    updated = client.put(
        "/api/org/settings",
        json={"name": "Demo Logistics Co.", "working_hours_start_min": 480, "working_hours_end_min": 1200},
    )
    assert updated.status_code == 200
    assert updated.json()["working_hours_start_min"] == 480

    # New orders now inherit the updated working hours.
    order = client.post(
        "/api/orders",
        json={"address": "y", "latitude": 19.0, "longitude": 72.8, "weight_kg": 5, "volume_m3": 0.1},
    ).json()
    assert order["window_start_min"] == 480 and order["window_end_min"] == 1200

    # Clean up so the shared session DB keeps a stable order count.
    client.delete(f"/api/orders/{order['id']}")
    client.put(
        "/api/org/settings",
        json={"name": "Demo Logistics Co.", "working_hours_start_min": 540, "working_hours_end_min": 1080},
    )


def test_orders_are_org_scoped(client, anon_client):
    from app.services.seeding import DEMO_EMAIL  # noqa: F401

    anon_client.post(
        "/api/auth/signup",
        json={
            "full_name": "Other", "company_name": "Other Co",
            "email": "orders-scope@example.com", "password": "Scoped123",
        },
    )
    # The new org has no orders even though the demo org has its full sample set.
    assert anon_client.get("/api/orders").json() == []
    assert len(client.get("/api/orders").json()) >= 93
