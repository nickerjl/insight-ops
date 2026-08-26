"""Deterministic error-simulation endpoints.

These make it possible to demonstrate the complete observability workflow
(500 error -> structured log -> fingerprint -> aggregation -> investigation)
without requiring a real production incident. Several endpoints raise
*language/runtime* errors (NameError, ZeroDivisionError, ...) that look like
real developer bugs rather than fake stubs, so fingerprints and the LLM
investigation are more realistic.
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


@router.get("/demo/error/undefined-name")
def demo_error_undefined_name() -> dict:
    """Realistic NameError, like `print(undefined_var)`."""
    payload = "payment ack"
    # The line below raises NameError at runtime (identifier is not defined).
    print(payload, _unseen_local)  # noqa: F821 - intentional NameError
    return {"status": "unreachable"}


@router.get("/demo/error/zero-division")
def demo_error_zerodivision() -> dict:
    """Realistic ZeroDivisionError."""
    denominator = 0
    return {"result": 100 // denominator}


@router.get("/demo/error/attr-error")
def demo_error_attribute() -> dict:
    """Realistic AttributeError."""
    user = {"id": 1}
    return {"profile": user.profile}


@router.get("/demo/error/key-error")
def demo_error_key() -> dict:
    """Realistic KeyError (missing dict key a dev assumed present)."""
    event = {"name": "payment"}
    return {"amount": event["amount"]}


@router.get("/demo/error/500")
def demo_error_500() -> dict:
    """Generic unhandled 500 with a traceback (kept for parity with the
    original demo when you just want a plain server error)."""
    raise RuntimeError("Simulated internal server error")


@router.get("/demo/error/payment-timeout")
def demo_error_payment_timeout() -> dict:
    """Deterministic upstream-payment timeout (5xx)."""
    raise PaymentProviderTimeout("Payment provider timed out")
