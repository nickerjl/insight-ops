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


def test_success_logs_info(monkeypatch, fake_redis):
    _capture["records"] = []
    teardown = _setup_capture(monkeypatch)
    try:
        mw = TaskLifecycleMiddleware()
        mw.after_process_message(_Broker(), _FakeMessage(retries=0), result="ok")
        successes = [r for r in _capture["records"] if r["message"] == "task success"]
        assert len(successes) == 1
        rec = successes[0]
        assert rec["level"] == "INFO"
        assert rec["task_id"] == "m1"
        assert rec["actor_name"] == "demo_task"
        assert rec["retry_count"] == 0
        assert rec["result"] == "ok"
    finally:
        teardown()


def test_retry_logs_error_with_counter(monkeypatch, fake_redis):
    _capture["records"] = []
    teardown = _setup_capture(monkeypatch)
    try:
        mw = TaskLifecycleMiddleware()
        mw.after_process_message(
            _Broker(),
            _FakeMessage(retries=1),
            exception=RuntimeError("boom"),
        )
        failures = [r for r in _capture["records"] if r["message"] == "task failure"]
        assert len(failures) == 1
        rec = failures[0]
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
        final = [r for r in _capture["records"] if "final" in r.get("message", "")]
        assert len(final) == 1
        assert final[0]["message"] == "task failure (final, dead-lettered)"
        # Aggregation alert raised for the final failure.
        assert calls == [("demo_task", "RuntimeError", "task:demo_task")]
    finally:
        teardown()


def test_task_failure_record_contains_traceback(monkeypatch, fake_redis):
    """The task-failure ring-buffer record must carry exception.traceback so
    expanded Dramatiq rows show a stack trace (parity with API error logs)."""
    from app.services.log_store import list_task_logs

    mw = TaskLifecycleMiddleware()
    try:
        raise RuntimeError("boom")
    except RuntimeError as exc:
        exception = exc
    mw.after_process_message(_Broker(), _FakeMessage(retries=1), exception=exception)
    logs = list_task_logs(fake_redis)
    assert logs
    failure = logs[0]
    assert failure["error_type"] == "RuntimeError"
    assert failure["exception"]["type"] == "RuntimeError"
    assert "Traceback" in failure["exception"]["traceback"]
    assert "boom" in failure["exception"]["message"]


def test_duration_and_status_field(monkeypatch, fake_redis):
    """duration_s must be non-null (computed via before_process_message start
    time) and the record must carry a status (success|failed)."""
    from app.services.log_store import list_task_logs

    mw = TaskLifecycleMiddleware()
    msg_success = _FakeMessage(retries=0)
    mw.before_process_message(_Broker(), msg_success)
    mw.after_process_message(_Broker(), msg_success, result="ok")

    logs = list_task_logs(fake_redis)
    success = logs[0]
    assert success["status"] == "success"
    assert success["duration_s"] is not None
    assert success["duration_s"] >= 0

    msg_fail = _FakeMessage(retries=1)
    mw.before_process_message(_Broker(), msg_fail)
    exc = None
    try:
        raise RuntimeError("boom")
    except RuntimeError as e:
        exc = e
    mw.after_process_message(_Broker(), msg_fail, exception=exc)

    logs2 = list_task_logs(fake_redis)
    failure = logs2[0]
    assert failure["status"] == "failed"
    assert failure["duration_s"] is not None
