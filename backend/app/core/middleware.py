"""Request-scoped middleware: correlation IDs + structured request logging."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.logging.context import reset_request_id, set_request_id

logger = logging.getLogger("app.request")

_REQUEST_ID_HEADER = "X-Request-ID"


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _endpoint_name(request: Request) -> str:
    route = request.scope.get("route")
    if route is not None and getattr(route, "name", None):
        return str(route.name)
    return request.url.path


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assign every request a request_id and expose it to application logs."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get(_REQUEST_ID_HEADER) or uuid.uuid4().hex
        request.state.request_id = request_id
        token = set_request_id(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            # Exception handlers own the 5xx log line (they include tracebacks).
            raise
        finally:
            reset_request_id(token)

        duration_ms = round((time.perf_counter() - started) * 1000, 2)

        extra = {
            "endpoint_name": _endpoint_name(request),
            "endpoint": request.url.path,
            "method": request.method,
            "status_code": response.status_code,
            "ip_address": _client_ip(request),
            "request_id": request_id,
            "duration_ms": duration_ms,
        }

        # Access-log line for every request that produced a response.
        # Exception handlers add a second, error-specific line with detail.
        if response.status_code < 400:
            logger.info("request completed", extra=extra)
        elif response.status_code < 500:
            logger.warning("request completed with client error", extra=extra)
        else:
            logger.error("request completed with server error", extra=extra)

        return response
