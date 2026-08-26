"""Tests for the Celery-style task lifecycle middleware (app/tasks/lifecycle).

Maps Celery hooks onto Dramatiq middleware, like the project that inspired it

    celery on_success  == TaskLifecycleMiddleware.after_process_message(result)
    celery on_failure  == (...) exception set
    celery on_retry    == failure with retries < max (Retries re-queues)

Acceptance criteria:
  - success -> INFO "task success" with task_id + actor_name
  - retry   -> ERROR "task failure" with retry_count < max
  - final   -> ERROR "task failure (final, dead-lettered)" + aggregation enqueued
"""

from __future__ import annotations

import logging

from app.tasks.lifecycle import TaskLifecycleMiddleware


class _FakeMessage:
    def __init__(self, message_id="m1", actor_name="demo_task", retries=0, queue_name="default"):
        self.message_id = message_id
        self.actor_name = actor_name
        self.queue_name = queue_name
        self.options = {"retries": retries}

    def decode(self):
        return [{}]


class _Broker:
    pass


_capture = {"records": [], "logger": None}


def _setup_capture(monkeypatch):
    import json

    from app.logging.formatters import JsonFormatter

    logger = logging.getLogger("app.tasks.lifecycle")

    class _Capture(logging.Handler):
        def emit(self, record):
            _capture["records"].append(json.loads(self.format(record)))

    handler = _Capture()
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.propagate = False

    def teardown():
        logger.removeHandler(handler)

    return teardown


def test_success_logs_info(monkeypatch):
    _capture["records"] = []
    teardown = _setup_capture(monkeypatch)
    try:
        mw = TaskLifecycleMiddleware()
        mw.after_process_message(_Broker(), _FakeMessage(retries=0), result="ok")
        assert len(_capture["records"]) == 1
        rec = _capture["records"][0]
        assert rec["message"] == "task success"
        assert rec["level"] == "INFO"
        assert rec["task_id"] == "m1"
        assert rec["actor_name"] == "demo_task"
        assert rec["retry_count"] == 0
        assert rec["result"] == "ok"
    finally:
        teardown()


def test_retry_logs_error_with_counter(monkeypatch):
    _capture["records"] = []
    teardown = _setup_capture(monkeypatch)
    try:
        mw = TaskLifecycleMiddleware()
        mw.after_process_message(
            _Broker(),
            _FakeMessage(retries=1),
            exception=RuntimeError("boom"),
        )
        assert len(_capture["records"]) == 1
        rec = _capture["records"][0]
        assert rec["message"] == "task failure"
        assert rec["level"] == "ERROR"
        assert rec["retry_count"] == 1
        assert rec["error_type"] == "RuntimeError"
        assert "boom" in rec["error_message"]
    finally:
        teardown()


def test_final_failure_logs_dead_lettered_and_aggregates(monkeypatch, fake_redis):
    _capture["records"] = []
    teardown = _setup_capture(monkeypatch)

    # Patch the aggregation enqueuer to record the call WITHOUT needing a broker.
    calls = []
    monkeypatch.setattr(
        "app.tasks.lifecycle._enqueue_error_aggregation",
        lambda actor, exc, endpoint: calls.append((actor, type(exc).__name__, endpoint)),
    )
    try:
        mw = TaskLifecycleMiddleware()
        mw.after_process_message(
            _Broker(),
            _FakeMessage(retries=3),  # == dramatiq_max_retries -> terminal
            exception=RuntimeError("boom"),
        )
        assert len(_capture["records"]) == 1
        rec = _capture["records"][0]
        assert rec["message"] == "task failure (final, dead-lettered)"
        # Aggregation alert raised for the final failure.
        assert calls == [("demo_task", "RuntimeError", "task:demo_task")]
    finally:
        teardown()
