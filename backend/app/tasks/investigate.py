"""Investigation task (Dramatiq actor).

Runs the investigation asynchronously (retrieval + DeepSeek) and stores the
result in the task store so the API/dashboard can poll it.

Transient LLM failures (timeout/5xx) are re-raised so Dramatiq retries with
backoff; after the retry budget is exhausted the task ends in "failed".
Non-transient failures (auth, malformed response) fail immediately.
"""

from __future__ import annotations

import json
import logging

import dramatiq
from dramatiq.middleware import CurrentMessage

from app.core.config import get_settings
from app.investigation.service import run_investigation
from app.services.deepseek import DeepSeekError
from app.services.redis_client import get_redis
from app.services.task_store import set_task_status

logger = logging.getLogger("app.tasks.investigation")

_settings = get_settings()


@dramatiq.actor(
    max_retries=_settings.dramatiq_max_retries,
    min_backoff=_settings.dramatiq_min_backoff_ms,
    max_backoff=_settings.dramatiq_max_backoff_ms,
)
def run_investigation_task(query: str, task_id: str) -> None:
    """Execute an investigation and persist its outcome."""
    redis = get_redis()
    set_task_status(redis, task_id, "running", query=query[:500])

    try:
        outcome = run_investigation(query)
    except DeepSeekError as exc:
        retries = CurrentMessage.get_current_message().options.get("retries", 0)
        if retries < _settings.dramatiq_max_retries:
            set_task_status(redis, task_id, "running", note="retrying transient LLM failure")
            logger.warning(
                "investigation transient failure, will retry",
                extra={"task_id": task_id, "retry_count": retries, "error_message": exc.message},
            )
            raise  # Dramatiq retries with backoff
        set_task_status(
            redis,
            task_id,
            "failed",
            error=json.dumps(
                {"type": exc.error_type, "message": f"{exc.message} (after retries)"}, default=str
            ),
        )
        logger.error(
            "investigation failed after retries",
            extra={"task_id": task_id, "retry_count": retries, "error_message": exc.message},
        )
        return

    if outcome["status"] == "completed":
        set_task_status(
            redis,
            task_id,
            "completed",
            result=json.dumps(outcome["result"], default=str),
        )
        logger.info(
            "investigation task completed",
            extra={"task_id": task_id, "query": query[:120]},
        )
    else:
        set_task_status(
            redis,
            task_id,
            "failed",
            error=json.dumps(outcome.get("error", {}), default=str),
        )
        logger.error(
            "investigation task failed",
            extra={"task_id": task_id, "query": query[:120], **outcome.get("error", {})},
        )
