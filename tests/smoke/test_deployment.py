"""Post-deployment API smoke tests (Phase 18).

These are API smoke tests — not browser E2E tests. They run against the
actually-deployed API after the pipeline deploys it. Any failure makes the
pipeline fail (non-zero pytest exit code).

Verified:
  - API reachable and routing works
  - /health and /ready return 200
  - success endpoint returns expected fields
  - critical async flow: error -> aggregation appears
  - investigation endpoint accepts a query
"""

from __future__ import annotations

import time

import requests


def test_health(base_url, http):
    response = http.get(f"{base_url}/health", timeout=10)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "insightops-api"
    assert "commit_hash" in body


def test_ready(base_url, http):
    response = http.get(f"{base_url}/ready", timeout=10)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "ready"
    assert body["checks"]["redis"] == "ok"


def test_success_endpoint(base_url, http):
    response = http.get(f"{base_url}/demo/success", timeout=10)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"


def test_error_endpoint_returns_expected_status(base_url, http):
    response = http.get(f"{base_url}/demo/error/500", timeout=10)
    assert response.status_code == 500
    assert response.json()["error"]["type"] == "RuntimeError"


def test_error_is_aggregated(base_url, http, wait_for_aggregation):
    # Generate a deterministic error and verify the async aggregation picks it up.
    response = http.get(f"{base_url}/demo/error/payment-timeout", timeout=10)
    assert response.status_code == 500

    agg = wait_for_aggregation("PaymentProviderTimeout", timeout=30)
    assert int(agg["count"]) >= 1
    assert agg["endpoint"] == "/demo/error/payment-timeout"
    assert len(agg["fingerprint"]) == 20


def test_investigation_can_be_created(base_url, http):
    response = http.post(
        f"{base_url}/api/investigations",
        json={"query": "Why are payment errors increasing?"},
        timeout=10,
    )
    assert response.status_code == 202, response.text
    body = response.json()
    assert body["investigation_id"]
    assert body["status"] == "queued"

    # The investigation completes asynchronously (degraded if no LLM key).
    deadline = time.time() + 30
    while time.time() < deadline:
        status = http.get(f"{base_url}/api/investigations/{body['investigation_id']}", timeout=10)
        assert status.status_code == 200, status.text
        state = status.json()
        if state["status"] in ("completed", "failed"):
            return
        time.sleep(2)
    raise AssertionError("investigation did not finish within 30s")
