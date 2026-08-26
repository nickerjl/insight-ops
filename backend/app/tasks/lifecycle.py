"""Task lifecycle observability middleware (Celery-style hooks for Dramatiq).

This is a Dramatiq analogue of a Celery pattern that exposes task lifecycle
callbacks (``on_success`` / ``on_failure`` / ``on_retry``):

  success  ─────────────────────────────► `after_process_message` (no exc)
  failure (non-terminal)  ──────────────► `after_process_message` (exc) + retry
  failure (retries exhausted)  ─────────► `after_process_message` (exc) + DEAD-LETTER
                                            (message consumed with retries == max)

Each event is logged as ONE structured JSON line (task_id, actor, retry_count,
queue, timedelta, error) to CloudWatch — mirroring ``celery_success_handling`` /
``celery_failure_handling`` / ``celery_retry_handling``. Failures also enqueue a
fingerprinted aggregation event (the project's error-alerting path, which in a
real deployment would fan out to Slack / PagerDuty / email).

In InsightOps, actor *business* logs (demo_task succeeded/failed) already exist;
this middleware adds the *framework* lifecycle view on top so every actor gets
uniform success/failure/retry logging without per-actor decorators.
"""

from __future__ import annotations

import logging
import time
import traceback as traceback_mod

import dramatiq
from dramatiq import Middleware

from app.core.config import get_settings
from app.logging.formatters import redact_text
from app.services.redis_client import get_redis

# `app.tasks.aggregate_errors.enqueue_error_aggregation` is imported lazily to
# avoid a circular import (this module is imported by app.tasks.broker).

logger = logging.getLogger("app.tasks.lifecycle")

# Actors for which we suppress noisy success logs (no-op internal machinery).
_SILENT_SUCCESS_ACTORS: set[str] = set()


def _decode_body(message: dramatiq.Message) -> dict:
    """Best-effort decode of the message body (list of args) into a dict."""
    try:
        body = message.decode()
    except Exception:  # pragma: no cover - defensive
        return {}
    raw = body[0] if body else {}
    return raw if isinstance(raw, dict) else {}


def _actor_name(message: dramatiq.Message) -> str:
    return getattr(message, "actor_name", "unknown") or "unknown"


def _settings_retries() -> int:
    try:
        return get_settings().dramatiq_max_retries
    except Exception:  # pragma: no cover
        return 3


def _enqueue_error_aggregation(actor: str, exc: Exception, endpoint: str) -> None:
    try:
        from app.tasks.aggregate_errors import enqueue_error_aggregation

        event = {
            "service": get_settings().service_name,
            "endpoint": endpoint,
            "method": "task",
            "status_code": 500,
            "error_type": type(exc).__name__,
            "error_message": redact_text(str(exc)) or type(exc).__name__,
            "commit_hash": get_settings().commit_hash,
            "request_id": None,
            "display_name": actor,
            "source": "task",
        }
        enqueue_error_aggregation(event)
    except Exception:  # pragma: no cover - never break task completion
        logger.warning("failed to enqueue lifecycle error aggregation", exc_info=True)


class TaskLifecycleMiddleware(Middleware):
    """Log every task success, failure and retry as structured JSON.

    Rough Celery-hook mapping for the interview:

        celery on_success  == after_process_message(result=..., exception=None)
        celery on_failure  == after_process_message(exception=...)
        celery on_retry    == failure while retries < max (Retries re-queues)
        celery (final)     == failure with retries == max -> aggregation alert
    """

    def after_process_message(self, broker, message, *, result=None, exception=None):
        actor = _actor_name(message)
        retry_count = int(message.options.get("retries", 0) or 0)
        elapsed_ms = _decode_body(message).get("_lifecycle_started_ms")
        duration_s = None
        if elapsed_ms is not None:
            duration_s = round((time.time() * 1000 - float(elapsed_ms)) / 1000, 3)

        common = {
            "task_id": message.message_id,
            "actor_name": actor,
            "retry_count": retry_count,
            "queue": message.queue_name,
            "duration_s": duration_s,
            "request_id": _decode_body(message).get("request_id"),
        }

        if exception is None:
            if actor in _SILENT_SUCCESS_ACTORS:
                return
            record = {**common, "result": str(result) if result is not None else None}
            logger.info("task success", extra=record)
            _buffer_task_log(record)
            return

        # Failure path: log it, and on the FINAL failure raise an aggregation alert.
        terminal = retry_count >= _settings_retries()
        message_kind = "task failure" if not terminal else "task failure (final, dead-lettered)"
        record = {
            **common,
            "error_type": type(exception).__name__,
            "error_message": redact_text(str(exception)) or type(exception).__name__,
            # Include the traceback so expanded Dramatiq rows show the stack
            # trace (mirroring the API error logs) for ease of debugging.
            "exception": {
                "type": type(exception).__name__,
                "message": redact_text(str(exception)) or type(exception).__name__,
                "traceback": "".join(
                    traceback_mod.format_exception(type(exception), exception, exception.__traceback__)
                ),
            },
        }
        logger.error(message_kind, extra=record, exc_info=exception)
        _buffer_task_log(record)
        if terminal:
            _enqueue_error_aggregation(actor, exception, endpoint=f"task:{actor}")


def _buffer_task_log(record: dict) -> None:
    """Write a task lifecycle record to the Redis ring buffer (best-effort)."""
    try:
        from app.services.log_store import push_task_log

        push_task_log(
            get_redis(),
            {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "source": "task",
                **record,
            },
        )
    except Exception:  # pragma: no cover - never break task completion
        logger.warning("failed to buffer task log", exc_info=True)
