"""Error aggregation tests (Phase 7 acceptance criteria).

System must represent: fingerprint | error type | endpoint | count |
first seen | last seen | commit hash — without PostgreSQL.
"""

from __future__ import annotations

from app.services.aggregation import (
    list_aggregations,
    list_recent_events,
    record_error_event,
)

BASE_EVENT = {
    "service": "insightops-api",
    "endpoint": "/api/payments",
    "method": "POST",
    "status_code": 500,
    "error_type": "PaymentProviderTimeout",
    "error_message": "Payment provider timed out",
    "commit_hash": "8f31a2c",
    "request_id": "req-1",
}


def test_repeated_error_aggregates_into_one_fingerprint(fake_redis):
    record_error_event(fake_redis, {**BASE_EVENT, "request_id": "req-1"})
    record_error_event(fake_redis, {**BASE_EVENT, "request_id": "req-2"})

    aggregations = list_aggregations(fake_redis)
    assert len(aggregations) == 1
    agg = aggregations[0]
    assert agg["error_type"] == "PaymentProviderTimeout"
    assert agg["endpoint"] == "/api/payments"
    assert agg["commit_hash"] == "8f31a2c"
    assert agg["count"] == "2"
    assert len(agg["fingerprint"]) == 20
    assert agg["first_seen"] <= agg["last_seen"]


def test_different_error_types_are_separate_aggregations(fake_redis):
    record_error_event(fake_redis, {**BASE_EVENT, "request_id": "r1"})
    record_error_event(
        fake_redis,
        {
            **BASE_EVENT,
            "request_id": "r2",
            "error_type": "RuntimeError",
            "error_message": "Simulated internal server error",
        },
    )

    aggregations = list_aggregations(fake_redis)
    assert len(aggregations) == 2
    types = {a["error_type"] for a in aggregations}
    assert types == {"PaymentProviderTimeout", "RuntimeError"}


def test_recent_events_ring_buffer(fake_redis):
    for i in range(10):
        record_error_event(fake_redis, {**BASE_EVENT, "request_id": f"r{i}"})

    events = list_recent_events(fake_redis, limit=50)
    assert len(events) == 10
    # Newest first (LIFO).
    assert events[0]["request_id"] == "r9"
    assert events[0]["fingerprint"]  # events carry the fingerprint


def test_event_fields_present_and_bounded(fake_redis):
    payload = record_error_event(fake_redis, BASE_EVENT)
    assert payload["status_code"] == 500
    assert payload["method"] == "POST"
    assert payload["request_id"] == "req-1"
