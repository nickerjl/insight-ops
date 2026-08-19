"""Aggregate router: mounts all feature routers.

Root routers (/health, /demo) are mounted directly. Feature routers (tasks,
errors, investigations) are mounted under the /api prefix; they are imported
inside the function so early-stage code can run before every feature module
exists. Once all modules are present this always mounts everything.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api import demo, health

root_router = APIRouter()
api_router = APIRouter()

root_router.include_router(health.router)
root_router.include_router(demo.router)


def mount_feature_routers() -> None:
    """Register feature routers under /api (best-effort, extended per phase)."""
    try:
        from app.api.errors import router as errors_router

        api_router.include_router(errors_router)
    except ImportError:  # pragma: no cover - not yet implemented
        pass

    try:
        from app.api.investigations import router as investigations_router

        api_router.include_router(investigations_router)
    except ImportError:  # pragma: no cover - not yet implemented
        pass

    try:
        from app.api.tasks import router as tasks_router

        api_router.include_router(tasks_router)
    except ImportError:  # pragma: no cover - not yet implemented
        pass
