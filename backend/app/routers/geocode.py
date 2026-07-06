"""Single-address geocoding for the order form's 'resolve address' button."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_org_id
from ..database import get_db
from ..services.geocoding import geocode

router = APIRouter(prefix="/api", tags=["geocode"])


class GeocodeRequest(BaseModel):
    address: str = Field(min_length=1, max_length=300)


class GeocodeResponse(BaseModel):
    found: bool
    latitude: float | None = None
    longitude: float | None = None


@router.post("/geocode", response_model=GeocodeResponse)
def resolve_address(
    payload: GeocodeRequest,
    db: Session = Depends(get_db),
    _org_id: int = Depends(get_current_org_id),  # auth only; result is org-agnostic
):
    result = geocode(db, payload.address)
    if result is None:
        return GeocodeResponse(found=False)
    return GeocodeResponse(found=True, latitude=result[0], longitude=result[1])
