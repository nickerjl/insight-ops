"""Investigation API tests (Phase 12 acceptance criteria).

The API can accept a natural-language investigation query and return a
task identifier; the async task produces a structured result that the API
exposes on poll.
"""

from __future__ import annotations

from dramatiq import Worker


def _process_queued(broker, queue: str = "default") -> None:
    worker = Worker(broker, worker_timeout=100)
    worker.start()
    try:
        broker.join(queue, timeout=20000)
    finally:
        worker.stop()


def test_create_investigation_returns_task_id(fake_redis, client):
    response = client.post("/api/investigations", json={"query": "Why are payment errors increasing?"})
    assert response.status_code == 202
    body = response.json()
    assert body["investigation_id"]
    assert body["status"] == "queued"


def test_investigation_validation(fake_redis, client):
    assert client.post("/api/investigations", json={"query": ""}).status_code == 422
    assert client.post("/api/investigations", json={"query": "x" * 501}).status_code == 422
    assert client.post("/api/investigations", json={}).status_code == 422


def test_full_async_flow_degraded_without_llm(fake_redis, client, broker):
    # Without DEEPSEEK_API_KEY the investigation completes in degraded mode.
    response = client.post("/api/investigations", json={"query": "payment errors"})
    investigation_id = response.json()["investigation_id"]

    assert client.get(f"/api/investigations/{investigation_id}").json()["status"] == "queued"

    _process_queued(broker)

    body = client.get(f"/api/investigations/{investigation_id}").json()
    assert body["status"] == "completed"
    assert "result" in body
    assert "summary" in body["result"]
    assert "not configured" in body["result"]["summary"]


def test_unknown_investigation_returns_404(fake_redis, client):
    response = client.get("/api/investigations/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["type"] == "TaskNotFoundError"


def test_llm_failure_marks_task_failed(fake_redis, client, broker, monkeypatch):
    from app.tasks import investigate as investigate_task_module

    def _boom(query):
        return {"status": "failed", "error": {"type": "DeepSeekError", "message": "boom"}}

    monkeypatch.setattr(investigate_task_module, "run_investigation", _boom)

    response = client.post("/api/investigations", json={"query": "why"})
    investigation_id = response.json()["investigation_id"]

    _process_queued(broker)

    body = client.get(f"/api/investigations/{investigation_id}").json()
    assert body["status"] == "failed"
    assert body["error"]["type"] == "DeepSeekError"


def test_transient_llm_failure_retries_then_fails(fake_redis, client, broker, monkeypatch):
    """Transient LLM errors trigger Dramatiq retries (1 attempt + 3 retries),
    then the task ends in 'failed' instead of dead-lettering silently."""
    from app.services.deepseek import DeepSeekError
    from app.tasks import investigate as investigate_task_module

    calls = {"n": 0}

    def _flaky(query):
        calls["n"] += 1
        raise DeepSeekError("transient boom", transient=True)

    monkeypatch.setattr(investigate_task_module, "run_investigation", _flaky)

    response = client.post("/api/investigations", json={"query": "why"})
    investigation_id = response.json()["investigation_id"]

    _process_queued(broker)

    body = client.get(f"/api/investigations/{investigation_id}").json()
    assert body["status"] == "failed"
    assert "after retries" in body["error"]["message"]
    assert calls["n"] == 4  # initial attempt + 3 retries (max_retries=3)
