"""Tests for the log ring buffers + /api/logs/recent endpoint."""

from __future__ import annotations

from app.services.log_store import (
    list_api_logs,
    list_task_logs,
    push_api_log,
    push_task_log,
)


def test_api_log_ring_buffer(fake_redis):
    for i in range(5):
        push_api_log(fake_redis, {"endpoint": f"/e{i}", "status_code": 200, "message": "hit"})
    logs = list_api_logs(fake_redis)
    assert len(logs) == 5
    # Newest first (LIFO).
    assert logs[0]["endpoint"] == "/e4"
    assert logs[4]["endpoint"] == "/e0"


def test_task_log_ring_buffer(fake_redis):
    push_task_log(fake_redis, {"actor_name": "demo_task", "retry_count": 2, "message": "task failure"})
    logs = list_task_logs(fake_redis)
    assert len(logs) == 1
    assert logs[0]["actor_name"] == "demo_task"
    assert logs[0]["retry_count"] == 2


def test_log_source_are_isolation_rings(fake_redis):
    push_api_log(fake_redis, {"endpoint": "/api", "message": "req"})
    push_task_log(fake_redis, {"actor_name": "t", "message": "task"})
    assert len(list_api_logs(fake_redis)) == 1
    assert len(list_task_logs(fake_redis)) == 1


def test_recent_endpoint_api_source(fake_redis, client):
    push_api_log(fake_redis, {"endpoint_name": "demo_success", "endpoint": "/demo/success", "status_code": 200})
    push_api_log(fake_redis, {"endpoint_name": "health", "endpoint": "/health", "status_code": 200})
    response = client.get("/api/logs/recent?source=api&limit=50")
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "api"
    assert body["count"] == 2
    assert body["logs"][0]["endpoint"] == "/health"


def test_recent_endpoint_dramatiq_source(fake_redis, client):
    push_task_log(fake_redis, {"actor_name": "demo_task", "retry_count": 1, "endpoint": "demo"})
    response = client.get("/api/logs/recent?source=dramatiq&limit=50")
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "dramatiq"
    assert body["logs"][0]["actor_name"] == "demo_task"
    assert body["logs"][0]["retry_count"] == 1


def test_recent_endpoint_invalid_source_422(fake_redis, client):
    assert client.get("/api/logs/recent?source=bogus").status_code == 422


def test_api_log_rings_preserve_source_field(fake_redis):
    push_api_log(fake_redis, {"endpoint": "/api/x", "message": "req", "source": "api"})
    logs = list_api_logs(fake_redis)
    assert logs[0]["source"] == "api"


def test_task_log_rings_preserve_source_field(fake_redis):
    push_task_log(fake_redis, {"actor_name": "demo", "message": "task", "source": "task"})
    logs = list_task_logs(fake_redis)
    assert logs[0]["source"] == "task"


def test_5xx_endpoint_produces_error_log_with_traceback(fake_redis, client):
    # Trigger a PaymentProviderTimeout through the app; the handler re-pushes
    # an ERROR api log carrying the exception/traceback.
    client.get("/demo/error/payment-timeout")
    logs = list_api_logs(fake_redis)
    error_logs = [l for l in logs if l.get("message") == "request failed"]
    assert error_logs, "expected a 'request failed' error log"
    rec = error_logs[0]
    assert rec["source"] == "api"
    assert rec["error_type"] == "PaymentProviderTimeout"
    assert rec["exception"]["type"] == "PaymentProviderTimeout"
    assert "Traceback" in rec["exception"]["traceback"]


def test_api_log_includes_request_body(fake_redis, client):
    """POST requests that hit the demo/api routes are logged with their
    redacted request body so the dashboard can inspect the payload."""
    client.post(
        "/api/tasks/demo",
        json={"kind": "success"},
    )
    logs = list_api_logs(fake_redis)
    post_row = next((l for l in logs if l.get("method") == "POST"), None)
    assert post_row is not None
    assert "request_body" in post_row
    assert "success" in post_row["request_body"]


def test_get_requests_have_no_body(fake_redis, client):
    client.get("/health")
    logs = list_api_logs(fake_redis)
    health = next((l for l in logs if l.get("endpoint") == "/health"), None)
    assert health is not None
    assert "request_body" not in health or health.get("request_body") is None
