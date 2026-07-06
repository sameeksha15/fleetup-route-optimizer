"""Package listing (read-only). Order CRUD lives in the orders router."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth.dependencies import get_current_org_id
from ..database import get_db

router = APIRouter(prefix="/api/packages", tags=["packages"])


@router.get("", response_model=list[schemas.PackageOut])
def list_packages(
    warehouse_id: int | None = None,
    db: Session = Depends(get_db),
    org_id: int = Depends(get_current_org_id),
):
    query = db.query(models.Package).filter(models.Package.organization_id == org_id)
    if warehouse_id is not None:
        query = query.filter(models.Package.warehouse_id == warehouse_id)
    return query.order_by(models.Package.id).all()
