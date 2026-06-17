"""Live smoke acceptance tests against a deployed instance (TEST-015 / TC-015-06).

Run with a BASE_URL pointing at a running deployment, e.g.:

    BASE_URL=https://mattdev.uber.space/picnic pytest -m acceptance

Verifies the deployment is healthy and the auth layer is wired (a protected API
route answers 401 unauthenticated rather than 5xx or a connection error).
"""

import httpx
import pytest

# A protected /api route (REQ-006): requires a valid session.
PROTECTED_ROUTE = "/api/receipts"

pytestmark = pytest.mark.acceptance


def test_health_endpoint_is_ok(base_url):
    response = httpx.get(f"{base_url}/health", timeout=10)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_protected_route_requires_authentication(base_url):
    response = httpx.get(f"{base_url}{PROTECTED_ROUTE}", timeout=10)

    assert response.status_code == 401
