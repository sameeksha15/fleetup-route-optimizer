"""Run the full optimization pipeline from the command line.

Usage (from backend/):
    python scripts/run_pipeline.py [--solver heuristic|dqn] [--weather clear|rain|storm]
                                   [--failure-rate 0.05] [--seed N] [--gnn]

Writes outputs/routes.csv and outputs/kpis.json, and prints the cost breakdown.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.geometry import OSRMGeometry, StraightLineGeometry
from engine.pipeline import PipelineConfig, generate_packages, run_pipeline
from engine.routing_api import OSRMClient
from engine.seeds import load_delivery_points, load_fleet, load_warehouses
from engine.travel_time import OfflineEstimator, OSRMProvider


def format_minutes(minutes: float) -> str:
    return (datetime.min + timedelta(minutes=minutes)).strftime("%I:%M %p")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fleet route optimization pipeline")
    parser.add_argument("--solver", choices=["heuristic", "dqn"], default="heuristic")
    parser.add_argument("--weather", choices=["live", "clear", "rain", "storm"], default="live")
    parser.add_argument("--online", action="store_true", help="use OSRM road times for the matrix")
    parser.add_argument("--straight", action="store_true", help="draw straight lines, skip OSRM geometry")
    parser.add_argument("--failure-rate", type=float, default=0.05)
    parser.add_argument("--gnn", action="store_true", help="also train the GNN (recorded, slow)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent.parent / "outputs")
    args = parser.parse_args()

    config = PipelineConfig(
        seed=args.seed,
        solver=args.solver,
        weather_mode=args.weather,
        online_routing=args.online,
        failure_rate=args.failure_rate,
        use_gnn=args.gnn,
    )
    warehouses = load_warehouses()
    trucks = load_fleet(warehouses)
    packages = generate_packages(load_delivery_points(), config)

    osrm = OSRMClient()
    offline = OfflineEstimator()
    provider = OSRMProvider(osrm, fallback=offline) if args.online else offline
    geometry = StraightLineGeometry() if args.straight else OSRMGeometry(osrm)

    print(
        f"Optimizing {len(packages)} packages across {len(trucks)} trucks "
        f"({config.solver} solver, {args.weather} weather, {geometry.name} geometry)..."
    )
    result = run_pipeline(warehouses, packages, trucks, provider, geometry, config)

    args.out.mkdir(parents=True, exist_ok=True)
    routes_csv = args.out / "routes.csv"
    with routes_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            ["truck_id", "trip", "kind", "package_id", "arrival", "departure", "window", "on_time"]
        )
        for tr in result.truck_results:
            for visit in tr.plan.visits:
                window = (
                    f"{format_minutes(visit.window.start_min)} - {format_minutes(visit.window.end_min)}"
                    if visit.window
                    else ""
                )
                writer.writerow(
                    [
                        tr.plan.truck_id,
                        visit.trip_number,
                        visit.kind,
                        visit.package_id if visit.package_id is not None else "",
                        format_minutes(visit.eta_min),
                        format_minutes(visit.departure_min),
                        window,
                        "" if visit.on_time is None else visit.on_time,
                    ]
                )

    (args.out / "kpis.json").write_text(json.dumps(result.kpis, indent=2), encoding="utf-8")

    print(f"\nRoutes written to {routes_csv}")
    print(f"Weather: {result.weather} ({result.weather_source})")
    print(f"Travel times: {result.provider} · geometry: {result.geometry_provider}")
    kpis = result.kpis
    print("\nCost breakdown:")
    for key, value in kpis["cost_breakdown"].items():
        print(f"  {key:10} {value:>10}")
    print("\nKPIs:")
    for key in (
        "stops_served",
        "failed_deliveries",
        "unassigned_packages",
        "on_time_rate",
        "total_drive_min",
        "total_distance_km",
        "total_waiting_min",
        "total_overtime_min",
        "total_trips",
        "avg_stops_per_trip",
        "avg_peak_load_utilization",
    ):
        print(f"  {key:26} {kpis[key]}")


if __name__ == "__main__":
    main()
