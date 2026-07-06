"""Warehouse and truck endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth.dependencies import get_current_org_id
from ..database import get_db

router = APIRouter(prefix="/api", tags=["fleet"])


@router.get("/warehouses", response_model=list[schemas.WarehouseOut])
def list_warehouses(db: Session = Depends(get_db), org_id: int = Depends(get_current_org_id)):
    return (
        db.query(models.Warehouse)
        .filter(models.Warehouse.organization_id == org_id)
        .order_by(models.Warehouse.id)
        .all()
    )


@router.post("/warehouses", response_model=schemas.WarehouseOut, status_code=201)
def create_warehouse(
    payload: schemas.WarehouseCreate,
    db: Session = Depends(get_db),
    org_id: int = Depends(get_current_org_id),
):
    warehouse = models.Warehouse(organization_id=org_id, **payload.model_dump())
    db.add(warehouse)
    db.commit()
    db.refresh(warehouse)
    return warehouse


@router.put("/warehouses/{warehouse_id}", response_model=schemas.WarehouseOut)
def update_warehouse(
    warehouse_id: int,
    payload: schemas.WarehouseCreate,
    db: Session = Depends(get_db),
    org_id: int = Depends(get_current_org_id),
):
    warehouse = _org_warehouse(db, org_id, warehouse_id)
    for key, value in payload.model_dump().items():
        setattr(warehouse, key, value)
    db.commit()
    db.refresh(warehouse)
    return warehouse


@router.delete("/warehouses/{warehouse_id}", status_code=204)
def delete_warehouse(
    warehouse_id: int,
    db: Session = Depends(get_db),
    org_id: int = Depends(get_current_org_id),
):
    warehouse = _org_warehouse(db, org_id, warehouse_id)
    trucks = db.query(models.Truck).filter(models.Truck.warehouse_id == warehouse_id).count()
    orders = db.query(models.Package).filter(models.Package.warehouse_id == warehouse_id).count()
    if trucks or orders:
        raise HTTPException(
            409,
            f"Warehouse is still used by {trucks} vehicle(s) and {orders} order(s). "
            "Reassign or remove them first.",
        )
    db.delete(warehouse)
    db.commit()


@router.get("/trucks", response_model=list[schemas.TruckOut])
def list_trucks(db: Session = Depends(get_db), org_id: int = Depends(get_current_org_id)):
    return (
        db.query(models.Truck)
        .filter(models.Truck.organization_id == org_id)
        .order_by(models.Truck.id)
        .all()
    )


def _org_warehouse(db: Session, org_id: int, warehouse_id: int) -> models.Warehouse:
    warehouse = db.get(models.Warehouse, warehouse_id)
    if warehouse is None or warehouse.organization_id != org_id:
        raise HTTPException(404, "Warehouse not found")
    return warehouse


@router.post("/trucks", response_model=schemas.TruckOut, status_code=201)
def create_truck(
    payload: schemas.TruckCreate,
    db: Session = Depends(get_db),
    org_id: int = Depends(get_current_org_id),
):
    _org_warehouse(db, org_id, payload.warehouse_id)
    truck = models.Truck(organization_id=org_id, **payload.model_dump())
    db.add(truck)
    db.commit()
    db.refresh(truck)
    return truck


@router.put("/trucks/{truck_id}", response_model=schemas.TruckOut)
def update_truck(
    truck_id: int,
    payload: schemas.TruckCreate,
    db: Session = Depends(get_db),
    org_id: int = Depends(get_current_org_id),
):
    truck = db.get(models.Truck, truck_id)
    if truck is None or truck.organization_id != org_id:
        raise HTTPException(404, "Truck not found")
    _org_warehouse(db, org_id, payload.warehouse_id)
    for key, value in payload.model_dump().items():
        setattr(truck, key, value)
    db.commit()
    db.refresh(truck)
    return truck


@router.delete("/trucks/{truck_id}", status_code=204)
def delete_truck(
    truck_id: int,
    db: Session = Depends(get_db),
    org_id: int = Depends(get_current_org_id),
):
    truck = db.get(models.Truck, truck_id)
    if truck is None or truck.organization_id != org_id:
        raise HTTPException(404, "Truck not found")
    db.delete(truck)
    db.commit()
