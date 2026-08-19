"""Error aggregation task (Dramatiq actor).

Consumes error events (enqueued by the exception handlers) and updates the
Redis aggregation store. Failures are retried with backoff per the project's
retry policy; the final failure is logged.
"""

from __future__ import annotations

import logging

import dramatiq

from app.core.config import get_settings
from app.services.aggregation import record_error_event
from app.services.redis_client import get_redis

logger = logging.getLogger("app.tasks.aggregation")

_settings = get_settings()


@dramatiq.actor(
    max_retries=_settings.dramatiq_max_retries,
    min_backoff=_settings.dramatiq_min_backoff_ms,
    max_backoff=_settings.dramatiq_max_backoff_ms,
)
def aggregate_error_event(event: dict) -> None:
    """Aggregate one error event into the Redis store."""
    try:
        payload = record_error_event(get_redis(), event)
        logger.info(
            "error aggregation updated",
            extra={
                "error_type": payload.get("error_type"),
                "endpoint": payload.get("endpoint"),
                "status_code": payload.get("status_code"),
                "error_fingerprint": payload.get("fingerprint"),
            },
        )
    except Exception:
        logger.error("error aggregation failed", exc_info=True)
        raise


def enqueue_error_aggregation(event: dict) -> None:
    """Enqueue an error event for aggregation (best-effort from handlers)."""
    aggregate_error_event.send(event)
