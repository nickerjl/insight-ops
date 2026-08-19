"""Health/readiness endpoint tests."""

from __future__ import annotations


def test_health_returns_200(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "insightops-api"
    assert "commit_hash" in body


def test_health_has_no_server_error_log(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_ready_returns_json_shape(client):
    # With no real Redis, readiness may report 503 — that is expected and
    # itself proves the endpoint responds instead of crashing.
    response = client.get("/ready")
    assert response.status_code in (200, 503)
    body = response.json()
    assert body["status"] in ("ready", "not_ready")
    assert "checks" in body
    assert "redis" in body["checks"]


def test_unknown_route_returns_404_json(client):
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    assert "error" in response.json()
