"""Order import: template, preview (validation + geocoding), and commit (upsert)."""

import io

import app.services.geocoding as geo


def _ok_orders(preview):
    return [r["order"] for r in preview["rows"] if r["status"] == "ok"]


def test_template_downloads(client):
    csv_resp = client.get("/api/orders/import/template?format=csv")
    assert csv_resp.status_code == 200
    assert "reference" in csv_resp.text.splitlines()[0]

    xlsx_resp = client.get("/api/orders/import/template?format=xlsx")
    assert xlsx_resp.status_code == 200
    assert "spreadsheetml" in xlsx_resp.headers["content-type"]


def test_preview_validates_rows_with_explicit_coords(client):
    csv = (
        "reference,recipient,address,lat,lng,weight,length,width,height,priority,window_start,window_end\n"
        "IMP-1,Alpha,Some Rd,19.10,72.90,20,50,40,30,high,09:00,12:00\n"
        "IMP-2,Beta,Other Rd,19.20,72.95,,,,,,,\n"  # no weight, no volume/dims -> errors
    )
    resp = client.post(
        "/api/orders/import/preview",
        files={"file": ("orders.csv", csv, "text/csv")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["summary"]["total"] == 2
    assert body["summary"]["ok"] == 1
    assert body["summary"]["errors"] == 1

    ok = _ok_orders(body)[0]
    assert ok["reference"] == "IMP-1"
    assert ok["latitude"] == 19.10 and ok["priority"] == 2
    assert abs(ok["volume_m3"] - 0.06) < 1e-6  # 50*40*30 cm^3


def test_preview_geocodes_missing_coordinates(client, monkeypatch):
    monkeypatch.setattr(geo, "_MIN_INTERVAL_S", 0.0)
    monkeypatch.setattr(
        geo.requests,
        "get",
        lambda *a, **k: type("R", (), {"raise_for_status": lambda self: None, "json": lambda self: [{"lat": "19.05", "lon": "72.88"}]})(),
    )
    csv = "reference,address,weight,volume\nG-1,Bandra West Mumbai,15,0.1\n"
    body = client.post(
        "/api/orders/import/preview", files={"file": ("o.csv", csv, "text/csv")}
    ).json()
    row = body["rows"][0]
    assert row["status"] == "ok"
    assert row["note"] == "geocoded"
    assert row["order"]["latitude"] == 19.05
    assert body["summary"]["geocoded"] == 1


def test_preview_resolves_warehouse_by_name(client):
    wh = client.post(
        "/api/warehouses", json={"name": "Alpha Depot", "latitude": 19.1, "longitude": 72.9}
    ).json()
    csv = (
        "reference,address,lat,lng,weight,volume,warehouse\n"
        "W-1,Rd,19.1,72.9,10,0.1,alpha depot\n"     # matched case-insensitively
        "W-2,Rd,19.1,72.9,10,0.1,Ghost Depot\n"      # not one of ours -> error
    )
    body = client.post(
        "/api/orders/import/preview", files={"file": ("o.csv", csv, "text/csv")}
    ).json()
    by_ref = {r["order"]["reference"]: r for r in body["rows"]}
    assert by_ref["W-1"]["status"] == "ok"
    assert by_ref["W-1"]["order"]["warehouse_id"] == wh["id"]
    assert by_ref["W-2"]["status"] == "error"


def test_commit_inserts_then_upserts_by_reference(client):
    csv = (
        "reference,recipient,address,lat,lng,weight,volume\n"
        "UP-1,First,Rd,19.1,72.9,10,0.1\n"
    )
    preview = client.post(
        "/api/orders/import/preview", files={"file": ("o.csv", csv, "text/csv")}
    ).json()
    orders = _ok_orders(preview)

    first = client.post("/api/orders/import/commit", json={"orders": orders}).json()
    assert first == {"added": 1, "updated": 0, "total": 1}

    # No window given -> inherits the org's working hours.
    created = next(o for o in client.get("/api/orders").json() if o["reference"] == "UP-1")
    assert created["window_start_min"] == 540 and created["window_end_min"] == 1080

    # Re-committing the same reference updates rather than duplicating.
    orders[0]["recipient"] = "Second"
    again = client.post("/api/orders/import/commit", json={"orders": orders}).json()
    assert again == {"added": 0, "updated": 1, "total": 1}
    matches = [o for o in client.get("/api/orders").json() if o["reference"] == "UP-1"]
    assert len(matches) == 1 and matches[0]["recipient"] == "Second"


def test_preview_reads_xlsx(client):
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(["reference", "address", "latitude", "longitude", "weight_kg", "volume_m3"])
    ws.append(["X-1", "Some Rd", 19.1, 72.9, 12, 0.2])
    buf = io.BytesIO()
    wb.save(buf)

    body = client.post(
        "/api/orders/import/preview",
        files={
            "file": (
                "orders.xlsx",
                buf.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    ).json()
    assert body["summary"]["ok"] == 1
    assert body["rows"][0]["order"]["reference"] == "X-1"
