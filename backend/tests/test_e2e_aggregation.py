"""End-to-end: simulated 500 -> structured log -> aggregation task -> API."""

from __future__ import annotations

from dramatiq import Worker


def test_error_endpoint_feeds_aggregation(fake_redis, client, broker):
    # Generate two identical 500 errors.
    assert client.get("/demo/error/payment-timeout").status_code == 500
    assert client.get("/demo/error/payment-timeout").status_code == 500

    # The exception handler enqueued aggregation tasks; process them.
    worker = Worker(broker, worker_timeout=100)
    worker.start()
    try:
        broker.join("default", timeout=20000)
    finally:
        worker.stop()

    body = client.get("/api/errors/aggregations").json()
    assert body["count"] == 1
    agg = body["aggregations"][0]
    assert agg["error_type"] == "PaymentProviderTimeout"
    assert agg["endpoint"] == "/demo/error/payment-timeout"
    assert agg["count"] == "2"

    recent = client.get("/api/errors/recent").json()
    assert recent["count"] == 2
    assert recent["events"][0]["error_type"] == "PaymentProviderTimeout"
