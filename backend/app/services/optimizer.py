"""Bridge between the API layer and the optimization engine.

Runs execute in a FastAPI background task: the run row tracks status so the
frontend can poll, and results are persisted as route visits + KPI JSON.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from engine.entities import Package, TimeWindow, Truck, Warehouse
from engine.geometry import GeometryProvider, OSRMGeometry, StraightLineGeometry, TomTomGeometry
from engine.pipeline import PipelineConfig, run_pipeline
from engine.routing_api import OSRMClient, TomTomClient
from engine.travel_time import OfflineEstimator, OSRMProvider, TomTomProvider, TravelTimeProvider

from .. import models
from ..config import get_settings
from ..database import SessionLocal


def build_providers(online_routing: bool) -> tuple[TravelTimeProvider, GeometryProvider]:
    """Pick travel-time and geometry providers from configuration.

    Geometry always follows roads (OSRM free by default, TomTom if a key is
    set). Travel times stay on the fast offline estimator unless online routing
    is requested, in which case the routing API drives the matrix too — with
    the offline estimator as a fallback if the service is unreachable.
    """
    settings = get_settings()
    offline = OfflineEstimator()
    osrm = OSRMClient(base_url=settings.osrm_base_url)

    if settings.tomtom_api_key:
        tomtom = TomTomClient(settings.tomtom_api_key)
        geometry: GeometryProvider = TomTomGeometry(tomtom)
        matrix = TomTomProvider(tomtom, fallback=offline) if online_routing else offline
    else:
        geometry = OSRMGeometry(osrm)
        matrix = OSRMProvider(osrm, fallback=offline) if online_routing else offline
    return matrix, geometry


def _load_engine_inputs(
    db: Session, org_id: int
) -> tuple[list[Warehouse], list[Package], list[Truck]]:
    warehouses = [
        Warehouse(w.id, w.name, w.latitude, w.longitude)
        for w in db.query(models.Warehouse).filter(models.Warehouse.organization_id == org_id).all()
    ]
    depots = {wh.id: wh for wh in warehouses}
    trucks = [
        Truck(
            id=t.id,
            capacity_kg=t.capacity_kg,
            volume_m3=t.volume_m3,
            warehouse_id=t.warehouse_id,
            latitude=depots[t.warehouse_id].latitude,
            longitude=depots[t.warehouse_id].longitude,
            length_cm=t.length_cm,
            width_cm=t.width_cm,
            height_cm=t.height_cm,
        )
        for t in db.query(models.Truck).filter(models.Truck.organization_id == org_id).all()
    ]
    packages = [
        Package(
            id=p.id,
            address=p.address,
            latitude=p.latitude,
            longitude=p.longitude,
            weight_kg=p.weight_kg,
            volume_m3=p.volume_m3,
            priority=p.priority,
            window=TimeWindow(p.window_start_min, p.window_end_min),
            warehouse_id=p.warehouse_id,
            length_cm=p.length_cm,
            width_cm=p.width_cm,
            height_cm=p.height_cm,
        )
        for p in db.query(models.Package).filter(models.Package.organization_id == org_id).all()
    ]
    return warehouses, packages, trucks


def execute_run(
    run_id: int,
    config: PipelineConfig,
    providers: tuple[TravelTimeProvider, GeometryProvider] | None = None,
) -> None:
    """Background task body: run the pipeline and persist the outcome.

    ``providers`` can be injected to force a specific travel-time/geometry pair
    (e.g. fully offline for the seeded demo run, so boot needs no network key).
    """
    db = SessionLocal()
    try:
        run = db.get(models.OptimizationRun, run_id)
        run.status = "running"
        org_id = run.organization_id
        db.commit()

        warehouses, packages, trucks = _load_engine_inputs(db, org_id)
        matrix_provider, geometry_provider = providers or build_providers(config.online_routing)
        result = run_pipeline(
            warehouses, packages, trucks, matrix_provider, geometry_provider, config
        )

        for tr in result.truck_results:
            for visit in tr.plan.visits:
                db.add(
                    models.RouteVisit(
                        run_id=run_id,
                        truck_id=tr.plan.truck_id,
                        trip_number=visit.trip_number,
                        kind=visit.kind,
                        package_id=visit.package_id,
                        latitude=visit.latitude,
                        longitude=visit.longitude,
                        eta_min=visit.eta_min,
                        departure_min=visit.departure_min,
                        window_start_min=visit.window.start_min if visit.window else None,
                        window_end_min=visit.window.end_min if visit.window else None,
                        on_time=visit.on_time,
                    )
                )

        run.kpis = result.kpis
        run.truck_stats = [
            {
                "truck_id": tr.plan.truck_id,
                "warehouse_id": tr.plan.warehouse_id,
                "packages": tr.packages,
                "trips": tr.plan.trips,
                "stops_served": tr.plan.stops_served,
                "failed": tr.plan.failed,
                "drive_min": tr.plan.drive_min,
                "distance_km": tr.plan.distance_km,
                "waiting_min": tr.plan.waiting_min,
                "overtime_min": tr.plan.overtime_min,
                "total_cost": tr.plan.cost_breakdown.get("total", 0.0),
                "peak_load_utilization": tr.peak_load_utilization,
            }
            for tr in result.truck_results
        ]
        run.geometries = {
            str(tr.plan.truck_id): {str(trip): geo for trip, geo in tr.trip_geometries.items()}
            for tr in result.truck_results
            if tr.trip_geometries
        }
        run.provider = result.provider
        run.geometry_provider = result.geometry_provider
        run.weather = result.weather
        run.weather_source = result.weather_source
        run.status = "completed"
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as exc:  # persist the failure so the UI can surface it
        db.rollback()
        run = db.get(models.OptimizationRun, run_id)
        run.status = "failed"
        run.error = str(exc)[:500]
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
    finally:
        db.close()


def seed_demo_run(org_id: int) -> None:
    """Create + execute one fully-offline run so a freshly-seeded org has a map.

    Uses the offline estimator + straight-line geometry with fixed 'clear'
    weather, so first boot needs no network and never spends the TomTom key.
    """
    db = SessionLocal()
    try:
        run = models.OptimizationRun(
            organization_id=org_id,
            status="queued",
            solver="heuristic",
            weather="clear",
            weather_source="pending",
            online_routing=False,
            failure_rate=0.05,
            provider="offline",
            geometry_provider="straight",
            use_gnn=False,
        )
        db.add(run)
        db.commit()
        run_id = run.id
    finally:
        db.close()

    execute_run(
        run_id,
        PipelineConfig(solver="heuristic", weather_mode="clear", online_routing=False),
        providers=(OfflineEstimator(), StraightLineGeometry()),
    )


def config_from_request(
    solver: str, weather_mode: str, online_routing: bool, failure_rate: float, use_gnn: bool, seed: int
) -> PipelineConfig:
    return PipelineConfig(
        seed=seed,
        solver=solver,
        weather_mode=weather_mode,
        online_routing=online_routing,
        failure_rate=failure_rate,
        use_gnn=use_gnn,
    )
