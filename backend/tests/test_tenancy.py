"""Multi-tenancy: each organization sees only its own data."""

import requests

from engine import routing_api


def _signup(client, email: str):
    resp = client.post(
        "/api/auth/signup",
        json={
            "full_name": "New Owner",
            "company_name": "New Co",
            "email": email,
            "password": "Newpass123",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp


def test_new_org_starts_empty(anon_client):
    """A fresh signup gets a blank workspace — the map has nothing to plot."""
    _signup(anon_client, "empty@newco.example")

    assert anon_client.get("/api/warehouses").json() == []
    assert anon_client.get("/api/trucks").json() == []
    assert anon_client.get("/api/packages").json() == []

    summary = anon_client.get("/api/kpis").json()
    assert summary["warehouses"] == 0
    assert summary["trucks"] == 0
    assert summary["packages"] == 0
    assert summary["latest_run"] is None


def test_empty_org_cannot_optimize(anon_client):
    _signup(anon_client, "noopt@newco.example")
    resp = anon_client.post("/api/optimize", json={"solver": "heuristic"})
    assert resp.status_code == 400


def test_orgs_are_isolated(client, anon_client):
    """The demo org's seed data is invisible to a different organization."""
    _signup(anon_client, "isolated@newco.example")

    assert len(client.get("/api/warehouses").json()) >= 9  # demo still sees its fleet
    assert anon_client.get("/api/warehouses").json() == []  # the new org sees nothing


def test_runs_do_not_leak_across_orgs(client, anon_client, monkeypatch):
    """A run created by one org cannot be fetched by another (no id guessing)."""

    def offline(*args, **kwargs):
        raise requests.ConnectionError("offline test")

    monkeypatch.setattr(routing_api.requests, "get", offline)

    resp = client.post(
        "/api/optimize", json={"solver": "heuristic", "weather_mode": "clear"}
    )
    assert resp.status_code == 202
    run_id = resp.json()["id"]
    assert client.get(f"/api/runs/{run_id}").status_code == 200

    _signup(anon_client, "nosnoop@newco.example")
    assert anon_client.get(f"/api/runs/{run_id}").status_code == 404
    assert anon_client.get(f"/api/runs/{run_id}/routes").status_code == 404
