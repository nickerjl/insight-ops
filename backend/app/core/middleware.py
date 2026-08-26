"""Request-scoped middleware: correlation IDs + structured request logging."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.config import get_settings
from app.logging.context import reset_request_id, set_request_id
from app.services.redis_client import get_redis

logger = logging.getLogger("app.request")

_REQUEST_ID_HEADER = "X-Request-ID"


def _client_ip(request: Request) -> str:
    # Trust X-Forwarded-For only when a trusted proxy (ALB/CloudFront)
    # terminates the connection (TRUST_PROXY_HEADERS=true). A direct client
    # can spoof this header; the value is used for logging/observability
    # only, never for auth.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded and get_settings().trust_proxy_headers:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _endpoint_name(request: Request) -> str:
    route = request.scope.get("route")
    if route is not None and getattr(route, "name", None):
        return str(route.name)
    return request.url.path


async def _capture_request_body(request: Request) -> str | None:
    """Read the request body (bounded + redacted) for logging.

    Returns None for bodyless methods (GET/HEAD) so the log row isn't cluttered.
    The body is cached on ``request._body`` by Starlette, so the actual handler
    can still read it afterwards.
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return None
    content_type = request.headers.get("content-type", "")
    if "json" not in content_type and "form" not in content_type:
        return None
    try:
        raw = await request.body()
        if not raw:
            return None
        body_bytes = raw[:2000]
        # Redact secret-like values before logging.
        from app.logging.formatters import redact_text

        return redact_text(body_bytes.decode("utf-8", errors="replace"))
    except Exception:
        return None


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assign every request a request_id and expose it to application logs."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get(_REQUEST_ID_HEADER) or uuid.uuid4().hex
        request.state.request_id = request_id
        token = set_request_id(request_id)
        started = time.perf_counter()

        # Capture the request body (bounded + redacted) WITHOUT breaking the
        # endpoint: Starlette caches the read body on request._body so a second
        # read by the handler returns the same bytes.
        request_body = await _capture_request_body(request)

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
        if request_body is not None:
            extra["request_body"] = request_body

        # Access-log line for every request that produced a response.
        # Exception handlers add a second, error-specific line with detail.
        if response.status_code < 400:
            logger.info("request completed", extra=extra)
        elif response.status_code < 500:
            logger.warning("request completed with client error", extra=extra)
        else:
            logger.error("request completed with server error", extra=extra)

        # Push the same envelope to a Redis ring buffer so the dashboard can
        # show API logs without hitting CloudWatch (persistent store). Clean
        # up indentation: this runs for EVERY request, not only 5xx.
        level = "INFO" if response.status_code < 400 else "ERROR"
        try:
            from app.services.log_store import push_api_log

            push_api_log(
                get_redis(),
                {
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "level": level,
                    "logger": "app.request",
                    "message": "request completed",
                    "source": "api",
                    **extra,
                },
            )
        except Exception:
            # Ring-buffer write must never break the request.
            logger.warning("failed to buffer api log", exc_info=True)

        return response
