"""Deterministic error-simulation endpoints.

These make it possible to demonstrate the complete observability workflow
(500 error -> structured log -> fingerprint -> aggregation -> investigation)
without requiring a real production incident.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.exceptions import PaymentProviderTimeout

router = APIRouter(tags=["demo"])


@router.get("/demo/success")
def demo_success() -> dict:
    """Deterministic success response."""
    return {"status": "ok", "message": "demo success"}


@router.get("/demo/error/400")
def demo_error_400() -> dict:
    """Deterministic client error (4xx)."""
    raise HTTPException(status_code=400, detail="Simulated client error")


@router.get("/demo/error/500")
def demo_error_500() -> dict:
    """Deterministic unhandled server error (5xx) with a traceback."""
    raise RuntimeError("Simulated internal server error")


@router.get("/demo/error/payment-timeout")
def demo_error_payment_timeout() -> dict:
    """Deterministic upstream-payment timeout (5xx)."""
    raise PaymentProviderTimeout("Payment provider timed out")
