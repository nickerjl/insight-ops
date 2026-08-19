"""Pytest fixtures.

A StubBroker is installed BEFORE any application module is imported so that
Dramatiq actors register against it and tests never need a real Redis.

``raise_server_exceptions=False`` is required because FastAPI routes the
generic ``Exception`` handler through Starlette's ServerErrorMiddleware,
which always re-raises the exception after sending the 500 response.
"""

from __future__ import annotations

import json
import logging

import dramatiq
import pytest
from dramatiq.brokers.stub import StubBroker
from fastapi.testclient import TestClient

# --- Install the stub broker before importing application modules ---------
_broker = StubBroker()
dramatiq.set_broker(_broker)

from app.main import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def broker() -> StubBroker:
    return _broker


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
