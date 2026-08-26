"""Centralized exception handlers.

Every error path produces:
  1. a structured JSON error response (consistent shape),
  2. a structured error log (with error_type, request context, and a
     fingerprint for server-side failures),
  3. (for 5xx) an asynchronous aggregation event enqueued for the worker.

Sensitive values are never included in logs or responses.
"""

from __future__ import annotations

import logging
import time

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import get_settings
from app.core.exceptions import AppError, error_payload
from app.services.fingerprint import build_fingerprint

logger = logging.getLogger("app.error")


def _request_context(request: Request) -> dict:
    route = request.scope.get("route")
    return {
        "endpoint_name": getattr(route, "name", None) or request.url.path,
        "endpoint": request.url.path,
        "method": request.method,
        "request_id": getattr(request.state, "request_id", None) or "unknown",
        "ip_address": request.client.host if request.client else "unknown",
    }


def _enqueue_aggregation(event: dict) -> None:
    """Best-effort enqueue of an error aggregation task (see Phase 7).

    Imported lazily so the API works even if the worker module is not
    available (e.g. during unit tests without a broker).
    """
    try:
        from app.tasks.aggregate_errors import enqueue_error_aggregation

        enqueue_error_aggregation(event)
    except Exception:  # pragma: no cover - never break the request on enqueue failure
        logger.warning("failed to enqueue error aggregation", exc_info=True)


def _error_event(request: Request, *, status_code: int, error_type: str, message: str) -> dict:
    settings = get_settings()
    return {
        "service": settings.service_name,
        "endpoint": request.url.path,
        "method": request.method,
        "status_code": status_code,
        "error_type": error_type,
        "error_message": message,
        "commit_hash": settings.commit_hash,
        "request_id": getattr(request.state, "request_id", None),
        "source": "api",
    }


def _push_error_log(request: Request, extra: dict, exception: Exception) -> None:
    """Push a 5xx API log WITH exception/traceback to the ring buffer.

    The middleware's normal envelope omits the traceback (that only lives in
    the CloudWatch log line); handlers re-push with ``exception`` so the
    dashboard expand shows the full debug info for ease of debugging.
    """
    try:
        from app.services.log_store import push_api_error_log
        from app.services.redis_client import get_redis

        record = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "level": "ERROR",
            "logger": "app.error",
            "message": "request failed",
            "source": "api",
            **extra,
        }
        push_api_error_log(get_redis(), record, exception)
    except Exception:  # pragma: no cover - never break the error response
        logger.warning("failed to buffer error log", exc_info=True)


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all exception handlers to the FastAPI app."""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        ctx = _request_context(request)
        status_code = exc.status_code
        detail = exc.detail

        extra = {**ctx, "status_code": status_code, "error_type": "HTTPException"}
        if isinstance(detail, str):
            extra["error_message"] = detail
        else:
            extra["error_message"] = "request validation failed"

        if status_code < 500:
            logger.warning("client error", extra=extra)
        else:
            logger.error("server error (http)", extra=extra)

        return JSONResponse(
            status_code=status_code,
            content={"error": {"type": "HTTPException", "message": detail}},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        ctx = _request_context(request)
        extra = {
            **ctx,
            "status_code": 422,
            "error_type": "RequestValidationError",
            "error_message": "request validation failed",
        }
        logger.warning("request validation error", extra=extra)

        # Strip raw input values and ctx so client-submitted data (which can
        # contain secrets or PII) is never echoed back or logged.
        errors = [
            {"loc": e.get("loc"), "type": e.get("type"), "msg": e.get("msg")}
            for e in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "type": "RequestValidationError",
                    "message": "Request validation failed",
                    "details": errors,
                }
            },
        )

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        ctx = _request_context(request)
        status_code = exc.status_code
        extra = {
            **ctx,
            "status_code": status_code,
            "error_type": exc.error_type,
            "error_message": exc.message,
        }
        logger.error("application error", extra=extra, exc_info=(type(exc), exc, exc.__traceback__))
        _push_error_log(request, extra, exc)

        _enqueue_aggregation(_error_event(request, status_code=status_code, error_type=exc.error_type, message=exc.message))

        return JSONResponse(status_code=status_code, content=error_payload(exc))

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        ctx = _request_context(request)
        settings = get_settings()
        status_code = 500
        error_type = type(exc).__name__
        error_message = str(exc) or error_type

        fp = build_fingerprint(
            service=settings.service_name,
            endpoint=request.url.path,
            exception_type=error_type,
            message=error_message,
        )

        extra = {
            **ctx,
            "status_code": status_code,
            "error_type": error_type,
            "error_message": error_message,
            "error_fingerprint": fp,
        }
        logger.error("unhandled exception", extra=extra, exc_info=exc)
        _push_error_log(request, extra, exc)

        _enqueue_aggregation(
            _error_event(request, status_code=status_code, error_type=error_type, message=error_message)
        )

        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "type": error_type,
                    "message": "Internal server error",
                }
            },
        )
