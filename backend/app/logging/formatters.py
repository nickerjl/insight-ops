"""JSON formatter producing one structured log line per record.

Field naming follows the README (timestamp, level, service, endpoint_name,
endpoint, method, status_code, ip_address, request_id, commit_hash,
error_type, error_message, exception {...}).

Sensitive values (tokens, passwords, keys, cookies, ...) are redacted before
serialization — secrets must never reach log output.
"""

from __future__ import annotations

import json
import logging
import re
import traceback as traceback_mod
from datetime import datetime, timezone
from typing import Any, Optional

from app.core.config import get_settings
from app.logging.context import get_request_id

# Substrings that mark a field as sensitive. Matching is case-insensitive.
SENSITIVE_FIELD_PATTERNS = (
    "password",
    "passwd",
    "token",
    "secret",
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "credential",
    "private_key",
    "access_key",
    "session_id",
    "x-api-key",
)

_REDACTED = "[REDACTED]"


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(pattern in lowered for pattern in SENSITIVE_FIELD_PATTERNS)


def redact(value: Any, key: str = "") -> Any:
    """Recursively replace sensitive values with a redaction marker."""
    if _is_sensitive_key(key):
        return _REDACTED
    if isinstance(value, dict):
        return {k: redact(v, str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(v, key) for v in value]
    return value


def _iso_timestamp(record: logging.LogRecord) -> str:
    return datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _exception_info(record: logging.LogRecord) -> Optional[dict]:
    if not record.exc_info:
        return None
    exc_type, exc_value, exc_tb = record.exc_info
    return {
        "type": exc_type.__name__ if exc_type else None,
        "message": str(exc_value) if exc_value else None,
        "traceback": "".join(traceback_mod.format_exception(*record.exc_info)),
    }


# Extra fields the middleware / handlers / tasks attach to a record.
_EXTRA_FIELDS = (
    "endpoint_name",
    "endpoint",
    "method",
    "status_code",
    "ip_address",
    "error_type",
    "error_message",
    "error_fingerprint",
    "duration_ms",
    "task_id",
    "job_id",
    "retry_count",
    "service",
)


class JsonFormatter(logging.Formatter):
    """Format a LogRecord as a single JSON object on one line."""

    def format(self, record: logging.LogRecord) -> str:
        settings = get_settings()

        payload: dict[str, Any] = {
            "timestamp": _iso_timestamp(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Application identity (stable across requests).
        payload["service"] = getattr(record, "service", settings.service_name)
        payload["commit_hash"] = getattr(record, "commit_hash", settings.commit_hash)

        # Request correlation.
        request_id = getattr(record, "request_id", None) or get_request_id()
        if request_id:
            payload["request_id"] = request_id

        # Known structured fields attached by callers.
        for field in _EXTRA_FIELDS:
            value = getattr(record, field, None)
            if value is not None and field not in payload:
                payload[field] = value

        # Exception details for server-side failures.
        exc_info = _exception_info(record)
        if exc_info:
            payload["exception"] = exc_info

        payload = redact(payload)
        return json.dumps(payload, ensure_ascii=False, default=str)
