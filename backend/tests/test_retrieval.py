"""Semantic retrieval tests (Phase 10 acceptance criteria).

  - natural-language queries retrieve relevant evidence
  - irrelevant logs are minimized
  - context size is bounded
"""

from __future__ import annotations

from app.investigation.retrieval import (
    build_evidence_context,
    retrieve_evidence,
    tokenize,
)
from app.services.aggregation import record_error_event


def _seed(fake_redis):
    record_error_event(
        fake_redis,
        {
            "service": "insightops-api",
            "endpoint": "/api/payments",
            "method": "POST",
            "status_code": 500,
            "error_type": "PaymentProviderTimeout",
            "error_message": "Payment provider timed out",
            "commit_hash": "8f31a2c",
        },
    )
    record_error_event(
        fake_redis,
        {
            "service": "insightops-api",
            "endpoint": "/api/payments",
            "method": "POST",
            "status_code": 500,
            "error_type": "PaymentProviderTimeout",
            "error_message": "Payment provider timed out",
            "commit_hash": "8f31a2c",
        },
    )
    record_error_event(
        fake_redis,
        {
            "service": "insightops-api",
            "endpoint": "/api/refunds",
            "method": "POST",
            "status_code": 400,
            "error_type": "RefundNotAllowed",
            "error_message": "Refund already processed",
            "commit_hash": "8f31a2c",
        },
    )


def test_tokenize_drops_stopwords_and_short_tokens():
    tokens = tokenize("Why are payment errors increasing after deployment?")
    assert "why" not in tokens
    assert "are" not in tokens
    assert "payment" in tokens
    assert "errors" in tokens
    assert "deployment" in tokens


def test_query_retrieves_relevant_aggregation(fake_redis):
    _seed(fake_redis)
    items = retrieve_evidence(fake_redis, "Why are payment errors increasing?")
    assert items, "expected at least one evidence item"

    top = items[0]
    assert top.error_type == "PaymentProviderTimeout"
    assert top.count == 2
    assert top.kind == "aggregation"
    # Payments ranked above refunds for a payments-focused query.
    assert top.endpoint == "/api/payments"


def test_irrelevant_evidence_minimized(fake_redis):
    _seed(fake_redis)
    items = retrieve_evidence(fake_redis, "refund already processed")
    assert items
    assert all("refund" in item.endpoint or "refund" in item.message for item in items[:1])


def test_context_bounded(fake_redis, monkeypatch):
    _seed(fake_redis)
    # Small char budget forces truncation.
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "retrieval_max_chars", 300)

    context = build_evidence_context(fake_redis, "payment errors")
    assert "query" in context
    assert context["deployment"] == "8f31a2c"
    assert isinstance(context["evidence"], list)

    import json

    rendered = json.dumps(context, default=str)
    assert len(rendered) <= 1000  # bounded (budget + overhead)


def test_context_contains_evidence_fields(fake_redis):
    _seed(fake_redis)
    context = build_evidence_context(fake_redis, "payment provider timeout")
    # All seeded occurrences (2 payment + 1 refund) are aggregated.
    assert context["total_errors_aggregated"] == 3
    item = context["evidence"][0]
    for key in ("fingerprint", "error_type", "endpoint", "count", "last_seen", "commit_hash", "score"):
        assert key in item
