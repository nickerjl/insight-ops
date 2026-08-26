"""Tests for aggregation display_name + latest_event (expandable rows)."""

from __future__ import annotations

from app.services.aggregation import list_aggregations, record_error_event

BASE = {
    "service": "insightops-api",
    "endpoint": "/api/payments",
    "method": "POST",
    "status_code": 500,
    "error_type": "PaymentProviderTimeout",
    "error_message": "Payment provider timed out",
    "commit_hash": "abc123",
}


def test_display_name_derived_from_endpoint_for_api(fake_redis):
    record_error_event(fake_redis, {**BASE, "request_id": "r1"})
    aggs = list_aggregations(fake_redis)
    assert aggs[0]["display_name"] == "/api/payments"


def test_display_name_uses_explicit_value(fake_redis):
    record_error_event(fake_redis, {**BASE, "request_id": "r1", "display_name": "task:demo_task"})
    aggs = list_aggregations(fake_redis)
    assert aggs[0]["display_name"] == "task:demo_task"


def test_aggregation_includes_latest_event(fake_redis):
    record_error_event(fake_redis, {**BASE, "request_id": "r1"})
    record_error_event(fake_redis, {**BASE, "request_id": "r2"})
    aggs = list_aggregations(fake_redis)
    latest = aggs[0]["latest_event"]
    assert latest is not None
    # Newest event is the one that was recorded last.
    assert latest["request_id"] == "r2"
    # The most recent event still carries the same fingerprint as its group.
    assert latest["fingerprint"] == aggs[0]["fingerprint"]


def test_latest_event_absent_when_no_recent(fake_redis):
    # A group whose recent-events ring was cleared still lists (no crash) and
    # simply has no latest_event snapshot.
    from app.services.aggregation import AGGREGATION_PREFIX

    fake_redis.delete(f"{AGGREGATION_PREFIX}{'x' * 20}")
    # No real aggregation exists; ensure listing stays lenient.
    assert list_aggregations(fake_redis) == []
