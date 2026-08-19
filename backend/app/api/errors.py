"""Error observability API: recent events + fingerprint aggregations."""

from __future__ import annotations

import redis
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.services.aggregation import list_aggregations, list_recent_events
from app.services.redis_client import get_redis

router = APIRouter(prefix="/errors", tags=["errors"])


def _redis_unavailable() -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"error": {"type": "RedisUnavailable", "message": "Error store unavailable"}},
    )


@router.get("/recent")
def recent_errors(limit: int = Query(50, ge=1, le=200)) -> dict:
    """Most recent error events observed by the aggregator."""
    try:
        events = list_recent_events(get_redis(), limit=limit)
    except redis.exceptions.RedisError:
        return _redis_unavailable()
    return {"events": events, "count": len(events)}


@router.get("/aggregations")
def error_aggregations(limit: int = Query(100, ge=1, le=500)) -> dict:
    """Recurring errors grouped by fingerprint."""
    try:
        aggregations = list_aggregations(get_redis(), limit=limit)
    except redis.exceptions.RedisError:
        return _redis_unavailable()
    return {"aggregations": aggregations, "count": len(aggregations)}
