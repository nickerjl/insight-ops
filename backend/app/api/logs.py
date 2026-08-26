"""Log visibility API: recent API + Dramatiq task logs from Redis ring buffers."""

from __future__ import annotations

import redis
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.services.log_store import list_api_logs, list_task_logs
from app.services.redis_client import get_redis

router = APIRouter(prefix="/logs", tags=["logs"])


def _redis_unavailable() -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"error": {"type": "RedisUnavailable", "message": "Log store unavailable"}},
    )


@router.get("/recent")
def recent_logs(
    source: str = Query("api", pattern="^(api|dramatiq)$"),
    limit: int = Query(100, ge=1, le=300),
) -> dict:
    """Return recent structured log envelopes from the Redis ring buffer.

    ``source=api``     -> HTTP request access logs (RequestContextMiddleware)
    ``source=dramatiq``-> task lifecycle logs (TaskLifecycleMiddleware)

    CloudWatch remains the persistent, queryable store; this is a fast,
    short-lived view for the dashboard.
    """
    try:
        if source == "dramatiq":
            records = list_task_logs(get_redis(), limit=limit)
        else:
            records = list_api_logs(get_redis(), limit=limit)
    except redis.exceptions.RedisError:
        return _redis_unavailable()
    return {"source": source, "logs": records, "count": len(records)}
