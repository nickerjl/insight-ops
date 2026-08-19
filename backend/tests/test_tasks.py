"""Async task tests (Phase 6 acceptance criteria).

API can enqueue -> worker consumes -> success/failure tracked.
Failed tasks retry with backoff (max 3 retries) and end in a final failure.
"""

from __future__ import annotations

import dramatiq
import pytest
from dramatiq import Worker

from app.tasks.demo_tasks import demo_task


def _process_queued(broker, queue: str = "default") -> None:
    """Start a worker, process everything currently queued, stop it."""
    worker = Worker(broker, worker_timeout=100)
    worker.start()
    try:
        broker.join(queue, timeout=20000)
    finally:
        worker.stop()


def test_demo_task_actor_options_match_policy():
    assert demo_task.options["max_retries"] == 3
    assert demo_task.options["min_backoff"] == 10  # tuned for tests
    assert demo_task.options["max_backoff"] == 100


def test_dispatch_and_success_flow(fake_redis, client, broker):
    response = client.post("/api/tasks/demo", json={"kind": "success"})
    assert response.status_code == 202
    task_id = response.json()["task_id"]
    assert response.json()["status"] == "queued"

    # Task starts queued, then the worker completes it.
    assert client.get(f"/api/tasks/{task_id}").json()["status"] == "queued"

    _process_queued(broker)

    status = client.get(f"/api/tasks/{task_id}").json()
    assert status["status"] == "completed"
    assert status["kind"] == "success"


def test_dispatch_and_failure_retries(fake_redis, client, broker):
    response = client.post("/api/tasks/demo", json={"kind": "failure"})
    assert response.status_code == 202
    task_id = response.json()["task_id"]

    _process_queued(broker)

    status = client.get(f"/api/tasks/{task_id}").json()
    assert status["status"] == "failed"
    assert "error" in status

    # The actor logged a final failure (retries exhausted).
    assert broker.dead_letters, "expected dead-lettered message after retries"


def test_unknown_task_returns_404(fake_redis, client):
    response = client.get("/api/tasks/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["type"] == "TaskNotFoundError"


def test_demo_task_validation(client):
    response = client.post("/api/tasks/demo", json={"kind": "explode"})
    assert response.status_code == 422


def test_api_does_not_block(fake_redis, client, broker):
    """Enqueue returns immediately with a task id (no synchronous wait)."""
    import time

    started = time.perf_counter()
    response = client.post("/api/tasks/demo", json={"kind": "success"})
    elapsed = time.perf_counter() - started
    assert response.status_code == 202
    assert elapsed < 1.0
