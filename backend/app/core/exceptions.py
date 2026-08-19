"""Centralized exception types.

The application raises typed exceptions; a single set of exception handlers
in ``app.main`` converts them into consistent JSON error responses and
structured error logs (including error_type + traceback for 5xx).
"""

from __future__ import annotations

from typing import Optional


class AppError(Exception):
    """Base class for application errors with a stable error type."""

    error_type = "AppError"
    status_code = 500

    def __init__(self, message: str, *, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code


class PaymentProviderTimeout(AppError):
    """Upstream payment provider did not respond in time (simulated)."""

    error_type = "PaymentProviderTimeout"
    status_code = 500


class InvestigationError(AppError):
    """Something went wrong while running an AI investigation."""

    error_type = "InvestigationError"
    status_code = 502


class TaskNotFoundError(AppError):
    """Requested asynchronous task / investigation does not exist."""

    error_type = "TaskNotFoundError"
    status_code = 404


def error_payload(exc: Exception) -> dict:
    """Build a consistent JSON error body for an exception."""
    return {
        "error": {
            "type": getattr(exc, "error_type", type(exc).__name__),
            "message": str(exc),
        }
    }
