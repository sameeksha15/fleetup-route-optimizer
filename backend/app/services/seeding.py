"""Seed sample data so the app is testable out of the box.

The demo account is seeded on first boot. The same routine also powers a
"load sample dataset" action any fresh organization can trigger, so it is
written to be organization-agnostic: warehouses are created with fresh ids and
the fleet / orders are re-pointed at them via an id map (never hard-coded ids).
Real organizations otherwise start empty and fill in their own data.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from engine.pipeline import PipelineConfig, generate_packages
from engine.seeds import load_delivery_points, load_fleet, load_warehouses

from .. import models
from ..auth.security import hash_password

# Demo account created on first boot so the app is testable out of the box.
DEMO_ORG_NAME = "Demo Logistics Co."
DEMO_USER_NAME = "Demo Admin"
DEMO_EMAIL = "demo@fleetup.app"
DEMO_PASSWORD = "Fleet@Demo2026"

# A few recipient names so the sample orders read realistically on the map.
_SAMPLE_RECIPIENTS = [
    "Sharma Traders", "Patel Stores", "Mehta & Co.", "Iyer Provisions",
    "Khan Electronics", "Reddy Mart", "D'Souza Bakery", "Gupta Hardware",
    "Naik Pharmacy", "Fernandes Grocers",
]


def seed_sample_data(db: Session, org_id: int) -> dict:
    """Populate an organization with the sample warehouses, fleet, and orders."""
    warehouses = load_warehouses()
    id_map: dict[int, int] = {}
    for wh in warehouses:
        row = models.Warehouse(
            organization_id=org_id, name=wh.name, latitude=wh.latitude, longitude=wh.longitude
        )
        db.add(row)
        db.flush()
        id_map[wh.id] = row.id

    fleet = load_fleet(warehouses)
    db.add_all(
        models.Truck(
            organization_id=org_id,
            name=f"Vehicle {truck.id}",
            capacity_kg=truck.capacity_kg,
            volume_m3=truck.volume_m3,
            length_cm=truck.length_cm,
            width_cm=truck.width_cm,
            height_cm=truck.height_cm,
            warehouse_id=id_map[truck.warehouse_id],
        )
        for truck in fleet
    )

    packages = generate_packages(load_delivery_points(), PipelineConfig(seed=42))
    db.add_all(
        models.Package(
            organization_id=org_id,
            reference=f"ORD-{i + 1:04d}",
            recipient=_SAMPLE_RECIPIENTS[i % len(_SAMPLE_RECIPIENTS)],
            address=pkg.address,
            latitude=pkg.latitude,
            longitude=pkg.longitude,
            weight_kg=pkg.weight_kg,
            volume_m3=pkg.volume_m3,
            length_cm=pkg.length_cm,
            width_cm=pkg.width_cm,
            height_cm=pkg.height_cm,
            priority=pkg.priority,
            window_start_min=pkg.window.start_min,
            window_end_min=pkg.window.end_min,
            warehouse_id=id_map[pkg.warehouse_id],
        )
        for i, pkg in enumerate(packages)
    )
    db.commit()
    return {"warehouses": len(warehouses), "vehicles": len(fleet), "orders": len(packages)}


def seed_demo_org(db: Session) -> None:
    """Create the demo organization + owner and its sample fleet, once."""
    if db.scalar(select(models.User).limit(1)) is not None:
        return
    org = models.Organization(name=DEMO_ORG_NAME)
    db.add(org)
    db.flush()
    db.add(
        models.User(
            organization_id=org.id,
            full_name=DEMO_USER_NAME,
            email=DEMO_EMAIL,
            password_hash=hash_password(DEMO_PASSWORD),
            role="owner",
        )
    )
    db.commit()
    seed_sample_data(db, org.id)

    # Pre-compute one offline route plan so the demo map isn't blank on first login.
    from .optimizer import seed_demo_run

    seed_demo_run(org.id)
