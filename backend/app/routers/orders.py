"""Delivery-order (package) endpoints: per-organization CRUD.

An "order" and a "package" are the same underlying entity; this router is the
user-facing CRUD surface, while ``/api/packages`` keeps its list + sample-load
endpoints. Orders that omit a delivery window inherit the org's working hours;
orders that omit a source warehouse are auto-assigned to the nearest one by the
engine at optimization time (hybrid assignment).
"""

import csv
import io

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth.dependencies import get_current_org_id
from ..database import get_db
from ..services.geocoding import geocode
from ..services.import_orders import TEMPLATE_EXAMPLE, TEMPLATE_HEADERS, parse_orders

router = APIRouter(prefix="/api/orders", tags=["orders"])

MAX_IMPORT_ROWS = 5000


def _org_order(db: Session, org_id: int, order_id: int) -> models.Package:
    order = db.get(models.Package, order_id)
    if order is None or order.organization_id != org_id:
        raise HTTPException(404, "Order not found")
    return order


def _validate_warehouse(db: Session, org_id: int, warehouse_id: int | None) -> None:
    if warehouse_id is None:
        return
    wh = db.get(models.Warehouse, warehouse_id)
    if wh is None or wh.organization_id != org_id:
        raise HTTPException(422, "Source warehouse not found in your organization.")


def _apply_defaults(db: Session, org_id: int, payload: schemas.PackageCreate) -> dict:
    """Resolve the delivery window against the org's working hours when omitted."""
    data = payload.model_dump()
    if data["window_start_min"] is None or data["window_end_min"] is None:
        org = db.get(models.Organization, org_id)
        data["window_start_min"] = org.working_hours_start_min
        data["window_end_min"] = org.working_hours_end_min
    return data


@router.get("", response_model=list[schemas.PackageOut])
def list_orders(db: Session = Depends(get_db), org_id: int = Depends(get_current_org_id)):
    return (
        db.query(models.Package)
        .filter(models.Package.organization_id == org_id)
        .order_by(models.Package.id)
        .all()
    )


@router.post("", response_model=schemas.PackageOut, status_code=201)
def create_order(
    payload: schemas.PackageCreate,
    db: Session = Depends(get_db),
    org_id: int = Depends(get_current_org_id),
):
    _validate_warehouse(db, org_id, payload.warehouse_id)
    order = models.Package(organization_id=org_id, **_apply_defaults(db, org_id, payload))
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@router.get("/{order_id}", response_model=schemas.PackageOut)
def get_order(
    order_id: int, db: Session = Depends(get_db), org_id: int = Depends(get_current_org_id)
):
    return _org_order(db, org_id, order_id)


@router.put("/{order_id}", response_model=schemas.PackageOut)
def update_order(
    order_id: int,
    payload: schemas.PackageCreate,
    db: Session = Depends(get_db),
    org_id: int = Depends(get_current_org_id),
):
    order = _org_order(db, org_id, order_id)
    _validate_warehouse(db, org_id, payload.warehouse_id)
    for key, value in _apply_defaults(db, org_id, payload).items():
        setattr(order, key, value)
    db.commit()
    db.refresh(order)
    return order


@router.delete("/{order_id}", status_code=204)
def delete_order(
    order_id: int, db: Session = Depends(get_db), org_id: int = Depends(get_current_org_id)
):
    order = _org_order(db, org_id, order_id)
    db.delete(order)
    db.commit()


# --- Bulk import (CSV / Excel) ---------------------------------------------


@router.get("/import/template")
def import_template(format: str = Query("csv", pattern="^(csv|xlsx)$")):
    """Download a blank order sheet with the canonical columns + one example row."""
    if format == "xlsx":
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.title = "Orders"
        ws.append(TEMPLATE_HEADERS)
        ws.append(TEMPLATE_EXAMPLE)
        buffer = io.BytesIO()
        wb.save(buffer)
        return Response(
            content=buffer.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=fleetup_orders_template.xlsx"},
        )

    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(TEMPLATE_HEADERS)
    writer.writerow(TEMPLATE_EXAMPLE)
    return Response(
        content=out.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=fleetup_orders_template.csv"},
    )


@router.post("/import/preview")
async def import_preview(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    org_id: int = Depends(get_current_org_id),
):
    """Parse + validate + geocode an uploaded file; return a per-row preview."""
    raw = await file.read()
    warehouses = [
        (w.id, w.name)
        for w in db.query(models.Warehouse).filter(models.Warehouse.organization_id == org_id)
    ]
    try:
        rows = parse_orders(
            raw,
            file.filename or "orders.csv",
            warehouses=warehouses,
            resolve_coords=lambda address: geocode(db, address),
        )
    except Exception as exc:  # malformed workbook / encoding, etc.
        raise HTTPException(400, f"Could not read the file: {exc}") from exc

    if len(rows) > MAX_IMPORT_ROWS:
        raise HTTPException(400, f"File has too many rows (max {MAX_IMPORT_ROWS}).")

    ok = sum(1 for r in rows if r["status"] == "ok")
    return {
        "rows": rows,
        "summary": {
            "total": len(rows),
            "ok": ok,
            "errors": len(rows) - ok,
            "geocoded": sum(1 for r in rows if r.get("note") == "geocoded"),
        },
    }


@router.post("/import/commit")
def import_commit(
    payload: schemas.ImportCommitRequest,
    db: Session = Depends(get_db),
    org_id: int = Depends(get_current_org_id),
):
    """Insert the confirmed rows, upserting existing orders by their reference."""
    added = updated = 0
    for order in payload.orders:
        _validate_warehouse(db, org_id, order.warehouse_id)
        data = _apply_defaults(db, org_id, order)
        existing = None
        if data["reference"]:
            existing = (
                db.query(models.Package)
                .filter(
                    models.Package.organization_id == org_id,
                    models.Package.reference == data["reference"],
                )
                .first()
            )
        if existing is not None:
            for key, value in data.items():
                setattr(existing, key, value)
            updated += 1
        else:
            db.add(models.Package(organization_id=org_id, **data))
            added += 1
        db.flush()  # so a repeated reference within the batch upserts too
    db.commit()
    return {"added": added, "updated": updated, "total": added + updated}
