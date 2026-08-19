"""Investigation API (Phase 12).

POST /api/investigations      -> dispatch async investigation, return id
GET  /api/investigations/{id} -> poll status / result
"""

from __future__ import annotations

import json

import redis
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.exceptions import TaskNotFoundError
from app.services.redis_client import get_redis
from app.services.task_store import create_task, get_task

router = APIRouter(prefix="/investigations", tags=["investigations"])


class InvestigationRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Natural-language investigation question.",
    )


@router.post("", status_code=202)
def create_investigation(payload: InvestigationRequest) -> dict:
    """Accept a natural-language query and dispatch an async investigation."""
    from app.tasks.investigate import run_investigation_task

    try:
        state = create_task(get_redis(), kind="investigation")
        run_investigation_task.send(payload.query, task_id=state["task_id"])
    except redis.exceptions.RedisError:
        # Remove the dangling queued task created above if enqueue failed.
        try:
            get_redis().delete(f"insightops:tasks:{state['task_id']}")
        except Exception:
            pass
        return JSONResponse(
            status_code=503,
            content={"error": {"type": "RedisUnavailable", "message": "Task dispatch unavailable"}},
        )
    return {
        "investigation_id": state["task_id"],
        "status": state["status"],
        "query": payload.query,
    }


@router.get("/{investigation_id}")
def get_investigation(investigation_id: str) -> dict:
    """Return the investigation status, result and error (if any)."""
    try:
        state = get_task(get_redis(), investigation_id)
    except redis.exceptions.RedisError:
        return JSONResponse(
            status_code=503,
            content={"error": {"type": "RedisUnavailable", "message": "Task store unavailable"}},
        )
    if state is None:
        raise TaskNotFoundError(f"Investigation {investigation_id} not found")

    response: dict = {
        "investigation_id": investigation_id,
        "status": state.get("status"),
    }
    if state.get("query"):
        response["query"] = state["query"]
    if state.get("result"):
        response["result"] = _loads(state["result"])
    if state.get("error"):
        response["error"] = _loads(state["error"])
    return response


def _loads(value: str) -> dict:
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {"value": parsed}
    except (json.JSONDecodeError, TypeError):
        return {"value": value}
