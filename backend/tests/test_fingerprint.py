"""Error fingerprinting tests.

Acceptance criteria (PROJECT_PLAN Phase 4):
  - same error -> same fingerprint
  - different errors -> different fingerprints
  - dynamic values do not fragment fingerprints
"""

from __future__ import annotations

from app.services.fingerprint import (
    build_aggregation_key,
    build_fingerprint,
    fingerprint,
    normalize_message,
)


def test_normalize_message_lowercases_and_collapses():
    assert normalize_message("  Payment Provider TIMED OUT\n ") == "payment provider timed out"


def test_normalize_message_normalizes_dynamic_values():
    message = 'Request failed for order 12345: uuid 9f8e7d6c-5b4a-3c21-0fed-cba987654321 retried 3 times'
    normalized = normalize_message(message)
    assert "12345" not in normalized
    assert "9f8e7d6c-5b4a-3c21-0fed-cba987654321" not in normalized
    assert "<n>" in normalized
    assert "<uuid>" in normalized


def test_same_error_same_fingerprint():
    fp1 = build_fingerprint(
        service="insightops-api",
        endpoint="/api/payments",
        exception_type="PaymentProviderTimeout",
        message="Payment provider timed out",
    )
    fp2 = build_fingerprint(
        service="insightops-api",
        endpoint="/api/payments",
        exception_type="PaymentProviderTimeout",
        message="Payment provider timed out",
    )
    assert fp1 == fp2
    assert len(fp1) == 20


def test_different_errors_different_fingerprints():
    fp1 = build_fingerprint(
        service="insightops-api",
        endpoint="/api/payments",
        exception_type="PaymentProviderTimeout",
        message="Payment provider timed out",
    )
    fp2 = build_fingerprint(
        service="insightops-api",
        endpoint="/api/payments",
        exception_type="RuntimeError",
        message="Payment provider timed out",
    )
    fp3 = build_fingerprint(
        service="insightops-api",
        endpoint="/api/refunds",
        exception_type="PaymentProviderTimeout",
        message="Payment provider timed out",
    )
    assert fp1 != fp2
    assert fp1 != fp3


def test_dynamic_values_do_not_fragment_fingerprint():
    fp1 = build_fingerprint(
        service="insightops-api",
        endpoint="/api/orders/12345",
        exception_type="OrderError",
        message="order 12345 not found for user 999",
    )
    fp2 = build_fingerprint(
        service="insightops-api",
        endpoint="/api/orders/67890",
        exception_type="OrderError",
        message="order 67890 not found for user 111",
    )
    assert fp1 == fp2


def test_fingerprint_is_sha256_prefix():
    key = build_aggregation_key(
        service="s", endpoint="/e", exception_type="T", message="boom"
    )
    fp = fingerprint(key)
    assert fp == fp.lower()
    assert len(fp) == 20
    # Deterministic for the same key.
    assert fingerprint(key) == fp
