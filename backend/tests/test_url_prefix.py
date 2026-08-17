"""
Configurable backend URL prefix (TEST-019).

Traces: ARCH-019
Verifies: REQ-019 (AC-019-01, AC-019-02)
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.api.dependencies import get_current_user
from backend.database import get_db
from backend.main import build_router
from backend.models import User


def _test_app(prefix: str, db_session: Session, test_user: User) -> TestClient:
    """A throwaway FastAPI app mounting build_router(prefix), authenticated
    as test_user — deliberately not the module-level `app`, so this stays a
    fast unit test with no scheduler/IMAP startup involved."""
    app = FastAPI()
    app.include_router(build_router(prefix))

    def _override_get_db():
        yield db_session

    def _override_get_current_user() -> User:
        return test_user

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user
    return TestClient(app)


# TC-019-01
# Given the backend router is built via build_router("")
# When a client requests GET /health, GET /, or GET /api/stats/budget
#   (authenticated) against a test app mounting that router
# Then each responds with 200 at its unprefixed path
# And GET /picnic/health returns 404 against that same test app
def test_empty_url_prefix_mounts_routes_at_root(db_session, test_user):
    # Arrange
    client = _test_app("", db_session, test_user)

    # Act
    health_response = client.get("/health")
    root_response = client.get("/")
    api_response = client.get("/api/stats/budget", params={"month": "2026-08"})
    prefixed_response = client.get("/picnic/health")

    # Assert
    assert health_response.status_code == 200
    assert health_response.json() == {"status": "ok"}
    assert root_response.status_code == 200
    assert api_response.status_code == 200
    assert prefixed_response.status_code == 404


# TC-019-02
# Given the backend router is built via build_router("/picnic")
#   (the default when URL_PREFIX is unset)
# When a client requests GET /picnic/health and GET /picnic/api/stats/budget
#   (authenticated) against a test app mounting that router
# Then each responds exactly as it does today (200, same payload shape)
# And GET /health (no prefix) returns 404 against that same test app
def test_default_url_prefix_keeps_picnic_prefixed_behavior(db_session, test_user):
    # Arrange
    client = _test_app("/picnic", db_session, test_user)

    # Act
    health_response = client.get("/picnic/health")
    api_response = client.get("/picnic/api/stats/budget", params={"month": "2026-08"})
    unprefixed_response = client.get("/health")

    # Assert
    assert health_response.status_code == 200
    assert health_response.json() == {"status": "ok"}
    assert api_response.status_code == 200
    assert unprefixed_response.status_code == 404
