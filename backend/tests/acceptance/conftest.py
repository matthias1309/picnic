"""Fixtures for the live acceptance suite (TEST-015).

The suite targets a running deployment via BASE_URL (e.g. the dev Uberspace,
https://mattdev.uber.space/picnic). When BASE_URL is unset the suite is skipped,
so the normal unit job — which never sets it — makes no network calls.
"""

import os

import pytest


@pytest.fixture(scope="session")
def base_url() -> str:
    url = os.environ.get("BASE_URL")
    if not url:
        pytest.skip("BASE_URL not set — acceptance tests run only against a live deployment")
    return url.rstrip("/")
