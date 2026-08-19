"""Pytest fixtures.

A StubBroker is installed BEFORE any application module is imported so that
Dramatiq actors register against it and tests never need a real Redis.
Backoff env vars are tuned before settings load so retry tests stay fast.

``raise_server_exceptions=False`` is required because FastAPI routes the
generic ``Exception`` handler through Starlette's ServerErrorMiddleware,
which always re-raises the exception after sending the 500 response.
"""

from __future__ import annotations

import json
import logging
import os

# Tune retry timing BEFORE application settings are cached.
os.environ.setdefault("DRAMATIQ_MIN_BACKOFF_MS", "10")
os.environ.setdefault("DRAMATIQ_MAX_BACKOFF_MS", "100")

import dramatiq  # noqa: E402
import pytest  # noqa: E402
from dramatiq.broker import default_middleware  # noqa: E402
from dramatiq.brokers.stub import StubBroker  # noqa: E402
from dramatiq.middleware import CurrentMessage  # noqa: E402
from dramatiq.middleware.prometheus import Prometheus  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

# --- Install the stub broker before importing application modules ---------
# Mirror the production broker: no Prometheus (not installed / not exposed)
# and add CurrentMessage so actors can read the current message id.
_middleware = [m() for m in default_middleware if m is not Prometheus]
_middleware.append(CurrentMessage())
_broker = StubBroker(middleware=_middleware)
dramatiq.set_broker(_broker)

from app.main import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def broker() -> StubBroker:
    return _broker


@pytest.fixture(autouse=True)
def _flush_queues(broker: StubBroker) -> None:
    """Drop leftover broker messages before every test.

    Actors enqueue onto the shared StubBroker even when no worker is
    running (e.g. error handlers during API tests); without flushing,
    unprocessed messages leak into later tests.
    """
    broker.flush_all()
    yield


@pytest.fixture
def fake_redis(monkeypatch):
    """Fake Redis patched into every module that resolves a client."""
    import fakeredis

    fake = fakeredis.FakeRedis(decode_responses=True)
    for module in (
        "app.api.tasks",
        "app.api.errors",
        "app.api.health",
        "app.tasks.demo_tasks",
        "app.tasks.aggregate_errors",
    ):
        monkeypatch.setattr(module + ".get_redis", lambda: fake, raising=False)
    return fake


class JsonCaptureHandler(logging.Handler):
    """Capture JSON-formatted log records emitted by a logger."""

    def __init__(self) -> None:
        super().__init__()
        from app.logging.formatters import JsonFormatter

        self.setFormatter(JsonFormatter())
        self.records: list[dict] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(json.loads(self.format(record)))


@pytest.fixture
def capture_logs():
    """Attach a JSON capture handler to a named logger.

    Usage::

        logger, records, teardown = capture_logs("app.request")
        try:
            client.get("/health")
        finally:
            teardown()
        assert records[0]["status_code"] == 200
    """

    def _capture(logger_name: str):
        logger = logging.getLogger(logger_name)
        handler = JsonCaptureHandler()
        old_propagate = logger.propagate
        logger.addHandler(handler)
        logger.propagate = False

        def teardown() -> None:
            logger.removeHandler(handler)
            logger.propagate = old_propagate

        return logger, handler.records, teardown

    return _capture
