"""Request-scoped context carried via contextvars.

The request ID is set by the request-logging middleware for the duration of a
request so that application-level and task-level logs emitted during that
request share the same correlation ID.
"""

from __future__ import annotations

import contextvars
from typing import Optional

request_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "request_id", default=None
)


def get_request_id() -> Optional[str]:
    return request_id_var.get()


def set_request_id(request_id: str) -> contextvars.Token:
    return request_id_var.set(request_id)


def reset_request_id(token: contextvars.Token) -> None:
    request_id_var.reset(token)
