"""FleetUp API: route optimization backend."""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.auth.dependencies import get_current_user
from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.routers import auth, fleet, geocode, optimization, orders, org, packages
from app.services.seeding import seed_demo_org


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_demo_org(db)
    yield


app = FastAPI(
    title="FleetUp API",
    description="Traffic-aware multi-trip fleet route optimization",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=True,  # required so the browser sends the session cookie
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth is public; every other API router requires a valid session.
app.include_router(auth.router)
_protected = [Depends(get_current_user)]
app.include_router(fleet.router, dependencies=_protected)
app.include_router(packages.router, dependencies=_protected)
app.include_router(orders.router, dependencies=_protected)
app.include_router(org.router, dependencies=_protected)
app.include_router(geocode.router, dependencies=_protected)
app.include_router(optimization.router, dependencies=_protected)


@app.get("/api/health")
def health():
    return {"status": "ok"}
