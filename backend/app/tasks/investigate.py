"""Investigation task (Dramatiq actor).

Runs the investigation asynchronously (retrieval + DeepSeek) and stores the
result in the task store so the API/dashboard can poll it.
"""

from __future__ import annotations

import json
import logging

import dramatiq

from app.core.config import get_settings
from app.investigation.service import run_investigation
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

    outcome = run_investigation(query)

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
        # Do not re-raise: LLM failures are business outcomes, not worker crashes.
