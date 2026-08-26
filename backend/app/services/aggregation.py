"""Error aggregation store (Redis).

Groups recurring errors by fingerprint and tracks:

    fingerprint | error_type | endpoint | count | first_seen | last_seen | commit_hash

Per PROJECT_PLAN Phase 7 there is intentionally no PostgreSQL: Redis holds
temporary aggregation state, CloudWatch remains the persistent log source.
"""

from __future__ import annotations

import json
import time
from typing import Optional

from app.core.config import get_settings
from app.logging.formatters import redact_text
from app.services.fingerprint import build_fingerprint

EVENTS_KEY = "insightops:error_events:recent"
AGGREGATION_PREFIX = "insightops:error_aggregation:"
MAX_RECENT_EVENTS = 200
MAX_MESSAGE_LENGTH = 300

_EVENT_FIELDS = (
    "service",
    "endpoint",
    "method",
    "status_code",
    "error_type",
    "error_message",
    "commit_hash",
    "request_id",
    "fingerprint",
    "display_name",
    "source",
    "exception",
)


def _display_name(event: dict) -> str:
    """Human-readable label for aggregation rows.

    API      -> endpoint_name (e.g. demo_error_500) falling back to endpoint
    Dramatiq -> the actor name; lifecycle events pass it via ``display_name``.
    """
    return str(
        event.get("display_name")
        or event.get("endpoint_name")
        or event.get("endpoint")
        or event.get("error_type", "UnknownError")
    )


def record_error_event(redis, event: dict) -> dict:
    """Record one error occurrence: append to recent events + bump aggregation.

    Returns the event enriched with its fingerprint.
    """
    settings = get_settings()
    # Scrub secret-like values out of free text BEFORE fingerprinting and
    # storage, so two occurrences differing only in an embedded rotating
    # token group under one fingerprint (and never reach the LLM prompt).
    error_message = redact_text(str(event.get("error_message", ""))) if event.get("error_message") else ""
    event["error_message"] = error_message

    fingerprint = build_fingerprint(
        service=event.get("service", settings.service_name),
        endpoint=event.get("endpoint", ""),
        exception_type=event.get("error_type", "UnknownError"),
        message=error_message,
    )
    event["fingerprint"] = fingerprint
    event.setdefault("service", settings.service_name)
    event.setdefault("commit_hash", settings.commit_hash)
    event["display_name"] = _display_name(event)

    now = time.time()
    payload = {field: event.get(field) for field in _EVENT_FIELDS}

    # Recent events: bounded ring buffer (oldest trimmed).
    redis.lpush(EVENTS_KEY, json.dumps(payload, default=str))
    redis.ltrim(EVENTS_KEY, 0, MAX_RECENT_EVENTS - 1)
    redis.expire(EVENTS_KEY, settings.error_aggregation_ttl)

    # Per-fingerprint aggregation.
    key = f"{AGGREGATION_PREFIX}{fingerprint}"
    message = str(event.get("error_message", ""))[:MAX_MESSAGE_LENGTH]
    pipe = redis.pipeline()
    pipe.hsetnx(key, "first_seen", now)
    pipe.hset(
        key,
        mapping={
            "fingerprint": fingerprint,
            "error_type": event.get("error_type", "UnknownError"),
            "endpoint": event.get("endpoint", ""),
            "method": event.get("method", ""),
            "service": event.get("service", settings.service_name),
            "commit_hash": event.get("commit_hash", settings.commit_hash),
            "message": message,
            "display_name": event["display_name"],
            "source": event.get("source", "api"),
            "last_seen": now,
        },
    )
    pipe.hincrby(key, "count", 1)
    pipe.expire(key, settings.error_aggregation_ttl)
    pipe.execute()

    return payload


def _as_float(value) -> float:
    """Coerce a Redis hash field to float; tolerate empty/garbage values."""
    try:
        return float(value) if value not in (None, "") else 0.0
    except (TypeError, ValueError):
        return 0.0


def list_aggregations(redis, limit: Optional[int] = None) -> list[dict]:
    """Return all fingerprint aggregations, most recently seen first.

    Each item carries the aggregation fields plus a ``latest_event`` snapshot
    (the most recent raw occurrence for that fingerprint) so the dashboard can
    expand a row to show the full latest log. This is additive — the fields
    the investigation service reads (error_type/endpoint/message/count/...) are
    unchanged, so expanding does NOT affect the LLM investigation.
    """
    settings = get_settings()
    items = []
    for key in redis.scan_iter(match=f"{AGGREGATION_PREFIX}*"):
        data = redis.hgetall(key)
        if not data:
            continue
        data.setdefault("count", "0")
        data.setdefault("first_seen", "")
        data.setdefault("last_seen", "")
        data["display_name"] = data.get("display_name")
        items.append(data)
    items.sort(key=lambda item: _as_float(item.get("last_seen")), reverse=True)
    if limit is not None:
        items = items[:limit]

    # Attach the latest raw event per fingerprint (newest-events ring buffer).
    by_fp: dict[str, dict] = {}
    for event in list_recent_events(redis, limit=MAX_RECENT_EVENTS):
        fp = event.get("fingerprint")
        if fp and fp not in by_fp:
            by_fp[fp] = event
    for item in items:
        item["latest_event"] = by_fp.get(item.get("fingerprint"))
    return items


def list_recent_events(redis, limit: int = 50) -> list[dict]:
    """Return the most recent error events (newest first)."""
    raw = redis.lrange(EVENTS_KEY, 0, max(limit, 1) - 1)
    events = []
    for item in raw:
        try:
            events.append(json.loads(item))
        except (json.JSONDecodeError, TypeError):
            continue
    return events
