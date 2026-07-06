"""API request/response schemas."""

from __future__ import annotations

from datetime import datetime, timedelta

from pydantic import BaseModel, ConfigDict, Field, model_validator


def format_minutes(minutes: float) -> str:
    """Minutes since midnight -> '09:30 AM'."""
    return (datetime.min + timedelta(minutes=minutes)).strftime("%I:%M %p")


class WarehouseBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class WarehouseCreate(WarehouseBase):
    pass


class WarehouseOut(WarehouseBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class TruckBase(BaseModel):
    name: str | None = Field(default=None, max_length=60)
    capacity_kg: float = Field(gt=0)
    volume_m3: float = Field(gt=0)
    length_cm: float | None = Field(default=None, gt=0)
    width_cm: float | None = Field(default=None, gt=0)
    height_cm: float | None = Field(default=None, gt=0)
    warehouse_id: int

    @model_validator(mode="after")
    def _dims_all_or_none(self):
        dims = (self.length_cm, self.width_cm, self.height_cm)
        if any(d is not None for d in dims) and not all(d is not None for d in dims):
            raise ValueError("Provide all three cargo-bay dimensions (length, width, height) or none.")
        return self


class TruckCreate(TruckBase):
    pass


class TruckOut(TruckBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class PackageBase(BaseModel):
    reference: str | None = Field(default=None, max_length=80)
    recipient: str | None = Field(default=None, max_length=120)
    address: str = Field(min_length=1, max_length=200)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    weight_kg: float = Field(gt=0)
    volume_m3: float | None = Field(default=None, gt=0)
    length_cm: float | None = Field(default=None, gt=0)
    width_cm: float | None = Field(default=None, gt=0)
    height_cm: float | None = Field(default=None, gt=0)
    priority: int = Field(default=1, ge=0, le=2)
    # Omit the window to inherit the organization's working hours (applied server-side).
    window_start_min: int | None = Field(default=None, ge=0, le=1439)
    window_end_min: int | None = Field(default=None, ge=0, le=1439)
    warehouse_id: int | None = None

    @model_validator(mode="after")
    def _derive_and_check(self):
        dims = (self.length_cm, self.width_cm, self.height_cm)
        has_all = all(d is not None for d in dims)
        if any(d is not None for d in dims) and not has_all:
            raise ValueError("Provide all three parcel dimensions (length, width, height) or none.")
        if self.volume_m3 is None:
            if has_all:
                self.volume_m3 = round(
                    self.length_cm * self.width_cm * self.height_cm / 1_000_000, 3
                )
            else:
                raise ValueError("Provide either volume_m3 or all three parcel dimensions.")
        if (self.window_start_min is None) != (self.window_end_min is None):
            raise ValueError("Provide both window_start_min and window_end_min, or neither.")
        if (
            self.window_start_min is not None
            and self.window_end_min is not None
            and self.window_start_min >= self.window_end_min
        ):
            raise ValueError("window_start_min must be before window_end_min.")
        return self


class PackageCreate(PackageBase):
    pass


class PackageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reference: str | None
    recipient: str | None
    address: str
    latitude: float
    longitude: float
    weight_kg: float
    volume_m3: float
    length_cm: float | None
    width_cm: float | None
    height_cm: float | None
    priority: int
    window_start_min: int
    window_end_min: int
    warehouse_id: int | None


class ImportCommitRequest(BaseModel):
    # The resolved rows returned by /import/preview (status == "ok").
    orders: list[PackageCreate]


class OrgSettingsUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    working_hours_start_min: int = Field(ge=0, le=1439)
    working_hours_end_min: int = Field(ge=0, le=1439)

    @model_validator(mode="after")
    def _order(self):
        if self.working_hours_start_min >= self.working_hours_end_min:
            raise ValueError("Working hours start must be before end.")
        return self


class OrgSettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    working_hours_start_min: int
    working_hours_end_min: int


class OptimizeRequest(BaseModel):
    solver: str = Field(default="heuristic", pattern="^(heuristic|dqn)$")
    weather_mode: str = Field(default="live", pattern="^(live|clear|rain|storm)$")
    online_routing: bool = False
    failure_rate: float = Field(default=0.05, ge=0.0, le=0.5)
    use_gnn: bool = False
    seed: int = 42


class VisitOut(BaseModel):
    truck_id: int
    trip_number: int
    kind: str
    package_id: int | None
    reference: str | None = None
    recipient: str | None = None
    latitude: float
    longitude: float
    eta_min: float
    eta: str
    departure: str
    window: str | None
    on_time: bool | None


class TruckRouteOut(BaseModel):
    truck_id: int
    warehouse_id: int
    color_index: int
    visits: list[VisitOut]
    # One road-following polyline (list of [lat, lon]) per trip, in order.
    geometry: list[list[list[float]]] = []


class RunSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    solver: str
    weather: str
    weather_source: str
    online_routing: bool
    failure_rate: float
    provider: str
    geometry_provider: str
    use_gnn: bool
    created_at: datetime
    completed_at: datetime | None
    error: str | None


class RunDetail(RunSummary):
    kpis: dict | None
    truck_stats: list | None


class RunRoutes(BaseModel):
    run_id: int
    routes: list[TruckRouteOut]
