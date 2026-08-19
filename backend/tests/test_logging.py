"""Structured logging tests (Phase 3 acceptance criteria)."""

from __future__ import annotations

import json
import logging

from app.logging.formatters import JsonFormatter, redact


def _make_record(message: str, level: int = logging.INFO, **extra) -> logging.LogRecord:
    record = logging.LogRecord(
        name="app.test", level=level, pathname=__file__, lineno=1, msg=message, args=(), exc_info=None
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_json_formatter_emits_structured_fields():
    formatter = JsonFormatter()
    record = _make_record(
        "request completed",
        level=logging.INFO,
        endpoint_name="demo_success",
        endpoint="/demo/success",
        method="GET",
        status_code=200,
        ip_address="127.0.0.1",
        request_id="abc-123",
        commit_hash="8f31a2c",
    )
    payload = json.loads(formatter.format(record))
    assert payload["level"] == "INFO"
    assert payload["service"] == "insightops-api"
    assert payload["endpoint_name"] == "demo_success"
    assert payload["endpoint"] == "/demo/success"
    assert payload["method"] == "GET"
    assert payload["status_code"] == 200
    assert payload["ip_address"] == "127.0.0.1"
    assert payload["request_id"] == "abc-123"
    assert payload["commit_hash"] == "8f31a2c"
    assert "timestamp" in payload


def test_json_formatter_includes_error_fields():
    formatter = JsonFormatter()
    record = _make_record(
        "unhandled exception",
        level=logging.ERROR,
        endpoint="/demo/error/500",
        method="GET",
        status_code=500,
        request_id="req-1",
        error_type="RuntimeError",
        error_message="boom",
        error_fingerprint="f" * 20,
    )
    payload = json.loads(formatter.format(record))
    assert payload["level"] == "ERROR"
    assert payload["error_type"] == "RuntimeError"
    assert payload["error_message"] == "boom"
    assert payload["error_fingerprint"] == "f" * 20


def test_sensitive_values_are_redacted():
    payload = redact(
        {
            "request_id": "abc",
            "headers": {"authorization": "Bearer secret-token", "x-api-key": "k123"},
            "body": {"password": "hunter2", "name": "alice"},
            "safe": {"count": 3},
        }
    )
    assert payload["headers"]["authorization"] == "[REDACTED]"
    assert payload["headers"]["x-api-key"] == "[REDACTED]"
    assert payload["body"]["password"] == "[REDACTED]"
    assert payload["body"]["name"] == "alice"
    assert payload["safe"]["count"] == 3
    assert payload["request_id"] == "abc"


def test_middleware_logs_request_with_correlation_id(client, capture_logs):
    logger, records, teardown = capture_logs("app.request")
    try:
        client.get("/health")
    finally:
        teardown()

    assert records, "expected at least one request log"
    log = records[0]
    assert log["endpoint"] == "/health"
    assert log["method"] == "GET"
    assert log["status_code"] == 200
    assert log["request_id"]
    assert log["service"] == "insightops-api"


def test_5xx_logs_error_details_and_fingerprint(client, capture_logs):
    logger, records, teardown = capture_logs("app.error")
    try:
        client.get("/demo/error/500")
    finally:
        teardown()

    assert records, "expected an error log"
    log = records[0]
    assert log["level"] == "ERROR"
    assert log["error_type"] == "RuntimeError"
    assert log["status_code"] == 500
    assert "exception" in log
    assert log["exception"]["type"] == "RuntimeError"
    assert "traceback" in log["exception"]
    assert len(log.get("error_fingerprint", "")) == 20


def test_4xx_logs_client_error(client, capture_logs):
    logger, records, teardown = capture_logs("app.error")
    try:
        client.get("/demo/error/400")
    finally:
        teardown()

    assert records
    log = records[0]
    assert log["level"] == "WARNING"
    assert log["status_code"] == 400
    assert log["error_type"] == "HTTPException"


def test_exception_traceback_captured():
    formatter = JsonFormatter()
    try:
        raise ValueError("boom")
    except ValueError:
        record = logging.LogRecord(
            name="app.test",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="unhandled",
            args=(),
            exc_info=__import__("sys").exc_info(),
        )
    payload = json.loads(formatter.format(record))
    assert payload["exception"]["type"] == "ValueError"
    assert "boom" in payload["exception"]["message"]
    assert "Traceback" in payload["exception"]["traceback"]
