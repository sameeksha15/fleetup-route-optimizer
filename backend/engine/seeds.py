"""Load seed data (warehouses, delivery points, fleet) from backend/data."""

from __future__ import annotations

import json
from pathlib import Path

from .entities import TimeWindow, Truck, Warehouse
from .pipeline import DeliveryPoint

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_warehouses(data_dir: Path = DATA_DIR) -> list[Warehouse]:
    raw = json.loads((data_dir / "warehouses.json").read_text(encoding="utf-8"))
    return [Warehouse(**item) for item in raw]


def load_delivery_points(data_dir: Path = DATA_DIR) -> list[DeliveryPoint]:
    raw = json.loads((data_dir / "delivery_stops.json").read_text(encoding="utf-8"))
    return [
        DeliveryPoint(
            address=item["address"],
            latitude=item["latitude"],
            longitude=item["longitude"],
            warehouse_id=item["warehouse_id"],
            window=TimeWindow(item["window_start_min"], item["window_end_min"]),
        )
        for item in raw
    ]


def load_fleet(warehouses: list[Warehouse], data_dir: Path = DATA_DIR) -> list[Truck]:
    depots = {wh.id: wh for wh in warehouses}
    raw = json.loads((data_dir / "fleet.json").read_text(encoding="utf-8"))
    return [
        Truck(
            id=item["id"],
            capacity_kg=item["capacity_kg"],
            volume_m3=item["volume_m3"],
            warehouse_id=item["warehouse_id"],
            latitude=depots[item["warehouse_id"]].latitude,
            longitude=depots[item["warehouse_id"]].longitude,
            length_cm=item.get("length_cm"),
            width_cm=item.get("width_cm"),
            height_cm=item.get("height_cm"),
        )
        for item in raw
    ]
