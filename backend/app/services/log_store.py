"""Log ring buffers (Redis).

The request middleware and task-lifecycle middleware each write a compact,
structured JSON envelope to a bounded Redis ring buffer. The frontend reads
them back via ``GET /api/logs/recent`` so the dashboard can show live API and
Dramatiq log tables *without* hitting CloudWatch (which remains the persistent,
queryable log store — see docs/logs-insights-queries.md).

Each buffer keeps only the most recent N records (bounded memory + TTL).
"""

from __future__ import annotations

import json
import time
from typing import Optional

from app.core.config import get_settings

API_LOGS_KEY = "insightops:api_logs:recent"
TASK_LOGS_KEY = "insightops:task_logs:recent"

MAX_API_LOGS = 300
MAX_TASK_LOGS = 200


def push_api_log(redis, record: dict) -> None:
    """Append one request log to the API ring buffer (lpush + trim + ttl)."""
    settings = get_settings()
    payload = _bounded_json(record)
    redis.lpush(API_LOGS_KEY, payload)
    redis.ltrim(API_LOGS_KEY, 0, MAX_API_LOGS - 1)
    redis.expire(API_LOGS_KEY, settings.error_aggregation_ttl)


def push_api_error_log(redis, record: dict, exception: Exception) -> None:
    """Append an ERROR request log with exception/traceback detail.

    Used by the exception handlers so expandable 5xx rows carry the full
    debug info (type, message, traceback) that the middleware envelope omits.
    """
    import traceback as traceback_mod

    record = dict(record)
    record["level"] = "ERROR"
    record["exception"] = {
        "type": type(exception).__name__,
        "message": str(exception),
        "traceback": "".join(traceback_mod.format_exception(type(exception), exception, exception.__traceback__)),
    }
    push_api_log(redis, record)


def push_task_log(redis, record: dict) -> None:
    """Append one task lifecycle record to the Dramatiq ring buffer."""
    settings = get_settings()
    payload = _bounded_json(record)
    redis.lpush(TASK_LOGS_KEY, payload)
    redis.ltrim(TASK_LOGS_KEY, 0, MAX_TASK_LOGS - 1)
    redis.expire(TASK_LOGS_KEY, settings.error_aggregation_ttl)


def list_api_logs(redis, limit: int = 100) -> list[dict]:
    return _list(redis, API_LOGS_KEY, limit)


def list_task_logs(redis, limit: int = 100) -> list[dict]:
    return _list(redis, TASK_LOGS_KEY, limit)


def _list(redis, key: str, limit: int) -> list[dict]:
    raw = redis.lrange(key, 0, max(limit, 1) - 1)
    records: list[dict] = []
    for item in raw:
        try:
            parsed = json.loads(item)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(parsed, dict):
            records.append(parsed)
    return records


def _bounded_json(record: dict) -> str:
    """Serialize a record, capping the total length and dropping deep or huge
    fields so the ring buffer stays small and fast."""
    # Only carry whitelisted top-level fields to keep it compact and safe.
    whitelist = {
        "timestamp",
        "level",
        "logger",
        "message",
        "endpoint_name",
        "endpoint",
        "method",
        "status_code",
        "ip_address",
        "request_id",
        "duration_ms",
        "task_id",
        "actor_name",
        "retry_count",
        "duration_s",
        "result",
        "error_type",
        "error_message",
        "queue",
        "source",
        # Exception detail (type/message/traceback) is included so the
        # dashboard can expand a 5xx row to the full debug info.
        "exception",
    }
    payload = {k: record[k] for k in whitelist if k in record}
    # Truncate the (potentially large) traceback but keep it readable.
    _cap_exception_depth(payload)
    text = json.dumps(payload, default=str)
    return text[:8000]


def _cap_exception_depth(record: dict) -> None:
    """Cap the exception.traceback length so the ring buffer stays small."""
    exc = record.get("exception")
    if isinstance(exc, dict) and isinstance(exc.get("traceback"), str):
        tb = exc["traceback"]
        exc["traceback"] = tb[:6000] + ("\n…" if len(tb) > 6000 else "")
