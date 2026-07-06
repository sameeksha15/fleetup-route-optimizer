import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# Point the app at a throwaway database before anything imports app.database.
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_fleet.db")

# Start each session from a clean slate (a prior crash could leave one behind).
_TEST_DB = BACKEND_DIR / "test_fleet.db"
if _TEST_DB.exists():
    try:
        _TEST_DB.unlink()
    except OSError:
        pass

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture()
def anon_client():
    """An unauthenticated API client."""
    from app.main import app

    with TestClient(app) as client:
        yield client


@pytest.fixture()
def client():
    """An API client authenticated as the seeded demo user."""
    from app.main import app
    from app.services.seeding import DEMO_EMAIL, DEMO_PASSWORD

    with TestClient(app) as client:
        resp = client.post(
            "/api/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD}
        )
        assert resp.status_code == 200, resp.text
        yield client


def pytest_sessionfinish(session, exitstatus):
    if _TEST_DB.exists():
        try:
            _TEST_DB.unlink()
        except OSError:
            pass
