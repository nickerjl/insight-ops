"""Demo task: demonstrates the asynchronous processing lifecycle.

``POST /api/tasks/demo`` enqueues this actor, which:
  - on ``success``: completes and logs success,
  - on ``failure``: raises, triggering Dramatiq retries with backoff
    (max 3 retries) and a final-failure log.

The API-generated task_id travels with the message, so task status stays
stable across retries (Dramatiq re-enqueues the same message on retry).
"""

from __future__ import annotations

import logging

import dramatiq
from dramatiq.middleware import CurrentMessage

from app.core.config import get_settings
from app.services.redis_client import get_redis
from app.services.task_store import set_task_status

logger = logging.getLogger("app.tasks.demo")

_settings = get_settings()


@dramatiq.actor(
    max_retries=_settings.dramatiq_max_retries,
    min_backoff=_settings.dramatiq_min_backoff_ms,
    max_backoff=_settings.dramatiq_max_backoff_ms,
)
def demo_task(kind: str, task_id: str) -> None:
    """Run a simulated task that succeeds or fails deterministically."""
    message = CurrentMessage.get_current_message()
    retries = message.options.get("retries", 0)

    set_task_status(get_redis(), task_id, "running", kind=kind, retries=retries)

    try:
        if kind == "success":
            logger.info(
                "demo task succeeded",
                extra={"task_id": task_id, "kind": kind, "retry_count": retries},
            )
            set_task_status(get_redis(), task_id, "completed", result="ok")
            return

        raise RuntimeError("Simulated task failure (retries expected)")
    except Exception as exc:
        logger.error(
            "demo task failed",
            extra={
                "task_id": task_id,
                "kind": kind,
                "retry_count": retries,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            },
            exc_info=True,
        )
        # Distinguish a transient failure (middleware will retry) from the
        # final one (retries exhausted -> dead-lettered), so the API/UI can
        # keep polling through the retry cycle.
        terminal = retries >= _settings.dramatiq_max_retries
        set_task_status(
            get_redis(),
            task_id,
            "failed",
            error=str(exc),
            retries=retries,
            terminal="true" if terminal else "false",
        )
        if terminal:
            logger.error(
                "demo task dead-lettered after retries exhausted",
                extra={"task_id": task_id, "retry_count": retries, "kind": kind},
            )
        raise
