"""Temporary task status storage (Redis).

Stores the lifecycle of asynchronously dispatched tasks so the API and the
dashboard can report status. State is short-lived (TTL) and re-creatable —
CloudWatch remains the persistent log source.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Optional

from app.core.config import get_settings

TASK_KEY_PREFIX = "insightops:tasks:"

STATUS_QUEUED = "queued"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"


def new_task_id() -> str:
    return uuid.uuid4().hex


def create_task(redis, kind: str, *, task_id: Optional[str] = None) -> dict:
    """Record a task as queued and return its initial state."""
    settings = get_settings()
    task_id = task_id or new_task_id()
    now = time.time()
    state = {
        "task_id": task_id,
        "kind": kind,
        "status": STATUS_QUEUED,
        "created_at": now,
        "updated_at": now,
    }
    redis.hset(f"{TASK_KEY_PREFIX}{task_id}", mapping=state)
    redis.expire(f"{TASK_KEY_PREFIX}{task_id}", settings.investigation_ttl)
    return state


def set_task_status(redis, task_id: str, status: str, **fields: Any) -> None:
    settings = get_settings()
    mapping = {"status": status, "updated_at": time.time(), **fields}
    redis.hset(f"{TASK_KEY_PREFIX}{task_id}", mapping=mapping)
    redis.expire(f"{TASK_KEY_PREFIX}{task_id}", settings.investigation_ttl)


def get_task(redis, task_id: str) -> Optional[dict]:
    state = redis.hgetall(f"{TASK_KEY_PREFIX}{task_id}")
    if not state:
        return None
    return state
