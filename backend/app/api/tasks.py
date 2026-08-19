"""Async task API: enqueue demo tasks and inspect task status."""

from __future__ import annotations

from typing import Literal

import redis
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.exceptions import TaskNotFoundError
from app.services.redis_client import get_redis
from app.services.task_store import create_task, get_task

router = APIRouter(prefix="/tasks", tags=["tasks"])


class DemoTaskRequest(BaseModel):
    kind: Literal["success", "failure"] = Field(
        ..., description="Whether the simulated task should succeed or fail."
    )


@router.post("/demo", status_code=202)
def dispatch_demo_task(payload: DemoTaskRequest) -> dict:
    """Enqueue a deterministic demo task (async, non-blocking)."""
    from app.tasks.demo_tasks import demo_task

    state = create_task(get_redis(), kind=f"demo:{payload.kind}")
    demo_task.send(payload.kind, task_id=state["task_id"])
    return {"task_id": state["task_id"], "status": state["status"]}


@router.get("/{task_id}")
def task_status(task_id: str) -> dict:
    """Return the current status of a previously dispatched task."""
    try:
        state = get_task(get_redis(), task_id)
    except redis.exceptions.RedisError:
        return JSONResponse(
            status_code=503,
            content={"error": {"type": "RedisUnavailable", "message": "Task store unavailable"}},
        )
    if state is None:
        raise TaskNotFoundError(f"Task {task_id} not found")
    return {"task_id": task_id, **state}
