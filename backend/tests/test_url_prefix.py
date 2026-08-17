"""
Configurable backend URL prefix (TEST-019).

Traces: ARCH-019
Verifies: REQ-019 (AC-019-01, AC-019-02)
"""

from http.cookies import SimpleCookie

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.api.dependencies import SESSION_COOKIE_NAME, get_current_user
from backend.config import settings
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


def _login_response(prefix: str, db_session: Session, monkeypatch):
    """POST <prefix>/api/auth/login as test_user against a fresh app built
    with build_router(prefix) — no get_current_user override, so the real
    login flow (and its Set-Cookie header) runs unmodified.

    Also patches the live settings.url_prefix to `prefix`, mirroring
    exactly how the real app wires this up (backend/main.py:
    `build_router(settings.url_prefix)`) — the cookie path is read from
    settings at request time (auth_routes._cookie_path()), not from
    build_router's argument, so the two must be kept in sync here too."""
    monkeypatch.setattr(settings, "url_prefix", prefix)
    app = FastAPI()
    app.include_router(build_router(prefix))

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    client = TestClient(app)
    return client.post(
        f"{prefix}/api/auth/login",
        json={"username": "alice", "password": "correct-password"},
    )


# Given the backend router is built via build_router("")
# When a client logs in successfully
# Then the session cookie's Path is "/" (not "/picnic"), so the browser
#   sends it back on every root-mounted route
# (Regression test for a prod incident: the cookie Path was hardcoded to
# "/picnic" independent of url_prefix, so every authenticated request 401'd
# once the backend was actually running with an empty prefix.)
def test_login_cookie_path_matches_empty_url_prefix(db_session, test_user, monkeypatch):
    # Arrange / Act
    response = _login_response("", db_session, monkeypatch)

    # Assert
    assert response.status_code == 200
    cookie = SimpleCookie()
    cookie.load(response.headers["set-cookie"])
    assert cookie[SESSION_COOKIE_NAME]["path"] == "/"


# Given the backend router is built via build_router("/picnic")
#   (the default when URL_PREFIX is unset)
# When a client logs in successfully
# Then the session cookie's Path is "/picnic", exactly as it is today
def test_login_cookie_path_matches_default_url_prefix(db_session, test_user, monkeypatch):
    # Arrange / Act
    response = _login_response("/picnic", db_session, monkeypatch)

    # Assert
    assert response.status_code == 200
    cookie = SimpleCookie()
    cookie.load(response.headers["set-cookie"])
    assert cookie[SESSION_COOKIE_NAME]["path"] == "/picnic"
