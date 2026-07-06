"""Organization settings: name and working hours (the default delivery window)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth.dependencies import get_current_org_id
from ..database import get_db
from ..services.seeding import seed_sample_data

router = APIRouter(prefix="/api/org", tags=["organization"])


@router.get("/settings", response_model=schemas.OrgSettingsOut)
def get_settings(db: Session = Depends(get_db), org_id: int = Depends(get_current_org_id)):
    return db.get(models.Organization, org_id)


@router.put("/settings", response_model=schemas.OrgSettingsOut)
def update_settings(
    payload: schemas.OrgSettingsUpdate,
    db: Session = Depends(get_db),
    org_id: int = Depends(get_current_org_id),
):
    org = db.get(models.Organization, org_id)
    org.name = payload.name
    org.working_hours_start_min = payload.working_hours_start_min
    org.working_hours_end_min = payload.working_hours_end_min
    db.commit()
    db.refresh(org)
    return org


@router.post("/load-sample")
def load_sample(db: Session = Depends(get_db), org_id: int = Depends(get_current_org_id)):
    """Populate an empty workspace with the sample warehouses, fleet, and orders."""
    has_data = (
        db.query(models.Warehouse).filter(models.Warehouse.organization_id == org_id).first()
        is not None
    )
    if has_data:
        raise HTTPException(409, "Workspace already has data; sample data is only for empty ones.")
    return seed_sample_data(db, org_id)
