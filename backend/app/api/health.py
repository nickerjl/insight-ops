"""Health and readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    """Liveness: the process is up and serving requests."""
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.service_name,
        "commit_hash": settings.commit_hash,
    }


@router.get("/ready")
def ready() -> JSONResponse:
    """Readiness: dependencies required to serve traffic are reachable.

    Redis is required for task dispatch; if it is unavailable the service is
    not ready to accept production traffic.
    """
    try:
        from app.services.redis_client import get_redis

        get_redis().ping()
        redis_ok = True
    except Exception:
        redis_ok = False

    status_code = 200 if redis_ok else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if redis_ok else "not_ready",
            "checks": {"redis": "ok" if redis_ok else "unavailable"},
        },
    )

