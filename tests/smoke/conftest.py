"""Shared smoke-test fixtures.

Smoke tests run against the ACTUAL deployed environment (GitLab CI smoke
stage). BASE_URL comes from the DEPLOYMENT_URL CI variable.
"""

from __future__ import annotations

import os
import time

import pytest
import requests

DEFAULT_TIMEOUT = 10


def get_base_url() -> str:
    url = os.environ.get("BASE_URL", "").rstrip("/")
    if not url:
        raise RuntimeError("BASE_URL environment variable is required (e.g. http://<ec2>:8000)")
    return url


@pytest.fixture(scope="session")
def base_url() -> str:
    return get_base_url()


@pytest.fixture(scope="session")
def http() -> requests.Session:
    session = requests.Session()
    session.headers["User-Agent"] = "insight-ops-smoke-tests"
    return session


@pytest.fixture
def wait_for_aggregation(http, base_url):
    """Poll /api/errors/aggregations until an error_type appears or timeout."""

    def _wait(error_type: str, timeout: int = 30, interval: int = 2) -> dict:
        deadline = time.time() + timeout
        while time.time() < deadline:
            response = http.get(f"{base_url}/api/errors/aggregations", timeout=DEFAULT_TIMEOUT)
            if response.status_code == 200:
                for agg in response.json().get("aggregations", []):
                    if agg.get("error_type") == error_type:
                        return agg
            time.sleep(interval)
        raise AssertionError(f"aggregation for {error_type!r} did not appear within {timeout}s")

    return _wait
