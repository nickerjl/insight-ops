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
