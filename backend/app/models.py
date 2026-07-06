"""Database models."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Organization(Base):
    """A company/tenant that owns a fleet. Created by its first (owner) user."""

    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    # Company working hours (minutes since midnight); the default delivery window
    # for orders that don't specify one. 540 = 09:00, 1080 = 18:00.
    working_hours_start_min: Mapped[int] = mapped_column(Integer, default=540)
    working_hours_end_min: Mapped[int] = mapped_column(Integer, default=1080)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    users: Mapped[list["User"]] = relationship(back_populates="organization")


class User(Base):
    """A person who signs in. Email is the unique login identifier."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="owner")  # owner|member
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Brute-force throttling (compared against naive UTC).
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    organization: Mapped[Organization] = relationship(back_populates="users")


class Warehouse(Base):
    __tablename__ = "warehouses"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)

    trucks: Mapped[list["Truck"]] = relationship(back_populates="warehouse")


class Truck(Base):
    __tablename__ = "trucks"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), index=True
    )
    name: Mapped[str | None] = mapped_column(String(60), nullable=True)
    capacity_kg: Mapped[float] = mapped_column(Float)
    volume_m3: Mapped[float] = mapped_column(Float)
    # Internal cargo-bay dimensions (cm), optional. When set, a parcel whose
    # longest sides exceed the bay is rejected as physically un-loadable.
    length_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    width_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"))

    warehouse: Mapped[Warehouse] = relationship(back_populates="trucks")


class Package(Base):
    __tablename__ = "packages"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), index=True
    )
    # The company's own order identifier (used to identify a stop on the map and
    # to dedupe re-imports); the delivery recipient's name.
    reference: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    recipient: Mapped[str | None] = mapped_column(String(120), nullable=True)
    address: Mapped[str] = mapped_column(String(200))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    weight_kg: Mapped[float] = mapped_column(Float)
    volume_m3: Mapped[float] = mapped_column(Float)
    # Parcel dimensions (cm), optional. Volume is derived from them when omitted.
    length_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    width_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    priority: Mapped[int] = mapped_column(Integer)
    window_start_min: Mapped[int] = mapped_column(Integer)
    window_end_min: Mapped[int] = mapped_column(Integer)
    warehouse_id: Mapped[int | None] = mapped_column(ForeignKey("warehouses.id"), nullable=True)


class GeocodeCache(Base):
    """Address -> coordinates, cached to avoid repeat calls to the geocoder.

    Shared across organizations (an address resolves the same for everyone) and
    keyed by a normalized query string. ``found=False`` remembers a miss so we
    don't retry a hopeless address on every import.
    """

    __tablename__ = "geocode_cache"

    id: Mapped[int] = mapped_column(primary_key=True)
    query: Mapped[str] = mapped_column(String(300), unique=True, index=True)
    found: Mapped[bool] = mapped_column(Boolean, default=False)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


class OptimizationRun(Base):
    __tablename__ = "optimization_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="queued")  # queued|running|completed|failed
    solver: Mapped[str] = mapped_column(String(30))
    weather: Mapped[str] = mapped_column(String(20), default="clear")  # resolved condition
    weather_source: Mapped[str] = mapped_column(String(60), default="")
    online_routing: Mapped[bool] = mapped_column(Boolean, default=False)
    failure_rate: Mapped[float] = mapped_column(Float, default=0.05)
    provider: Mapped[str] = mapped_column(String(30))
    geometry_provider: Mapped[str] = mapped_column(String(30), default="straight")
    use_gnn: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    kpis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    truck_stats: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # {truck_id: {trip_number: [[lat, lon], ...]}} road polylines
    geometries: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)

    visits: Mapped[list["RouteVisit"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="RouteVisit.id"
    )


class RouteVisit(Base):
    """One scheduled arrival (depot departure or delivery) within a run."""

    __tablename__ = "route_visits"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("optimization_runs.id"))
    truck_id: Mapped[int] = mapped_column(Integer)
    trip_number: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(12))  # depart|delivery|failed|reload|break|return
    package_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    eta_min: Mapped[float] = mapped_column(Float)
    departure_min: Mapped[float] = mapped_column(Float)
    window_start_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    window_end_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    on_time: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    run: Mapped[OptimizationRun] = relationship(back_populates="visits")
