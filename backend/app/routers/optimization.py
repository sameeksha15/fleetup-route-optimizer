"""Optimization run endpoints: trigger, poll, and fetch results."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth.dependencies import get_current_org_id
from ..database import get_db
from ..services.optimizer import build_providers, config_from_request, execute_run

router = APIRouter(prefix="/api", tags=["optimization"])


def _org_run(db: Session, org_id: int, run_id: int) -> models.OptimizationRun:
    run = db.get(models.OptimizationRun, run_id)
    if run is None or run.organization_id != org_id:
        raise HTTPException(404, "Run not found")
    return run


@router.post("/optimize", response_model=schemas.RunSummary, status_code=202)
def start_run(
    payload: schemas.OptimizeRequest,
    tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    org_id: int = Depends(get_current_org_id),
):
    # Nothing to optimize until the org has at least a fleet and some orders.
    trucks = db.query(models.Truck).filter(models.Truck.organization_id == org_id).count()
    packages = db.query(models.Package).filter(models.Package.organization_id == org_id).count()
    if trucks == 0 or packages == 0:
        raise HTTPException(
            400, "Add warehouses, at least one vehicle, and some orders before optimizing."
        )

    # Provider names are known up front; the resolved weather is filled in when
    # the run completes (weather here shows the requested mode until then).
    matrix_provider, geometry_provider = build_providers(payload.online_routing)
    run = models.OptimizationRun(
        organization_id=org_id,
        status="queued",
        solver=payload.solver,
        weather=payload.weather_mode,
        weather_source="pending",
        online_routing=payload.online_routing,
        failure_rate=payload.failure_rate,
        provider=matrix_provider.name,
        geometry_provider=geometry_provider.name,
        use_gnn=payload.use_gnn,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    config = config_from_request(
        payload.solver,
        payload.weather_mode,
        payload.online_routing,
        payload.failure_rate,
        payload.use_gnn,
        payload.seed,
    )
    tasks.add_task(execute_run, run.id, config)
    return run


@router.get("/runs", response_model=list[schemas.RunDetail])
def list_runs(
    limit: int = 20,
    db: Session = Depends(get_db),
    org_id: int = Depends(get_current_org_id),
):
    return (
        db.query(models.OptimizationRun)
        .filter(models.OptimizationRun.organization_id == org_id)
        .order_by(models.OptimizationRun.created_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/runs/latest", response_model=schemas.RunDetail)
def latest_run(db: Session = Depends(get_db), org_id: int = Depends(get_current_org_id)):
    run = (
        db.query(models.OptimizationRun)
        .filter(
            models.OptimizationRun.organization_id == org_id,
            models.OptimizationRun.status == "completed",
        )
        .order_by(models.OptimizationRun.completed_at.desc())
        .first()
    )
    if run is None:
        raise HTTPException(404, "No completed runs yet")
    return run


@router.get("/runs/{run_id}", response_model=schemas.RunDetail)
def get_run(run_id: int, db: Session = Depends(get_db), org_id: int = Depends(get_current_org_id)):
    return _org_run(db, org_id, run_id)


@router.get("/runs/{run_id}/routes", response_model=schemas.RunRoutes)
def run_routes(
    run_id: int, db: Session = Depends(get_db), org_id: int = Depends(get_current_org_id)
):
    run = _org_run(db, org_id, run_id)
    if run.status != "completed":
        raise HTTPException(409, f"Run is {run.status}")

    routes: dict[int, schemas.TruckRouteOut] = {}
    truck_warehouses = {t["truck_id"]: t["warehouse_id"] for t in run.truck_stats or []}
    geometries = run.geometries or {}
    # Identify each stop by the company's own order reference / recipient.
    order_labels = {
        p.id: (p.reference, p.recipient)
        for p in db.query(
            models.Package.id, models.Package.reference, models.Package.recipient
        ).filter(models.Package.organization_id == org_id)
    }
    for visit in run.visits:
        if visit.truck_id not in routes:
            # JSON object keys are strings; trips are stored keyed by str(trip_number).
            truck_geometry = geometries.get(str(visit.truck_id), {})
            ordered = [truck_geometry[k] for k in sorted(truck_geometry, key=int)]
            routes[visit.truck_id] = schemas.TruckRouteOut(
                truck_id=visit.truck_id,
                warehouse_id=truck_warehouses.get(visit.truck_id, 0),
                color_index=len(routes),
                visits=[],
                geometry=ordered,
            )
        window = None
        if visit.window_start_min is not None and visit.window_end_min is not None:
            window = (
                f"{schemas.format_minutes(visit.window_start_min)}"
                f" - {schemas.format_minutes(visit.window_end_min)}"
            )
        reference, recipient = order_labels.get(visit.package_id, (None, None))
        routes[visit.truck_id].visits.append(
            schemas.VisitOut(
                truck_id=visit.truck_id,
                trip_number=visit.trip_number,
                kind=visit.kind,
                package_id=visit.package_id,
                reference=reference,
                recipient=recipient,
                latitude=visit.latitude,
                longitude=visit.longitude,
                eta_min=visit.eta_min,
                eta=schemas.format_minutes(visit.eta_min),
                departure=schemas.format_minutes(visit.departure_min),
                window=window,
                on_time=visit.on_time,
            )
        )
    return schemas.RunRoutes(run_id=run_id, routes=list(routes.values()))


@router.get("/kpis")
def kpis(db: Session = Depends(get_db), org_id: int = Depends(get_current_org_id)):
    """Dashboard summary: fleet counts plus the latest completed run's KPIs."""
    run = (
        db.query(models.OptimizationRun)
        .filter(
            models.OptimizationRun.organization_id == org_id,
            models.OptimizationRun.status == "completed",
        )
        .order_by(models.OptimizationRun.completed_at.desc())
        .first()
    )
    return {
        "warehouses": db.query(models.Warehouse)
        .filter(models.Warehouse.organization_id == org_id)
        .count(),
        "trucks": db.query(models.Truck)
        .filter(models.Truck.organization_id == org_id)
        .count(),
        "packages": db.query(models.Package)
        .filter(models.Package.organization_id == org_id)
        .count(),
        "latest_run": schemas.RunSummary.model_validate(run).model_dump() if run else None,
        "kpis": run.kpis if run else None,
    }
