"""InsightOps FastAPI application entrypoint.

Run locally (no Docker):

    cd backend
    pip install -r requirements.txt
    uvicorn app.main:app --reload --port 8000

Run inside Docker:

    uvicorn app.main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.router import api_router, mount_feature_routers, root_router
from app.core.config import get_settings
from app.core.handlers import register_exception_handlers
from app.core.middleware import RequestContextMiddleware
from app.logging.setup import setup_logging

logger = logging.getLogger("app.main")


def create_app() -> FastAPI:
    settings = get_settings()
    settings.validate_runtime()
    setup_logging(settings)

    app = FastAPI(
        title="InsightOps API",
        description="Observability and AI-assisted debugging API.",
        version=__version__,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestContextMiddleware)

    register_exception_handlers(app)

    app.include_router(root_router)
    mount_feature_routers()
    app.include_router(api_router, prefix=settings.api_prefix)

    logger.info(
        "InsightOps API starting",
        extra={
            "endpoint_name": "startup",
            "commit_hash": settings.commit_hash,
            "app_env": settings.app_env,
        },
    )
    return app


app = create_app()
