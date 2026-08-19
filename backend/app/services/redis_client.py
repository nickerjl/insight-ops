"""Shared Redis client.

Used for:
  - the Dramatiq broker (see ``app.tasks.broker``)
  - temporary error-aggregation state
  - investigation result storage

Redis holds only short-lived, re-creatable state (per PROJECT_PLAN Phase 7).
CloudWatch remains the persistent log source.
"""

from __future__ import annotations

import redis as redis_lib

from app.core.config import get_settings

_client = None


def get_redis() -> redis_lib.Redis:
    """Return a lazily-initialized Redis client (safe to call from tests)."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = redis_lib.Redis.from_url(settings.redis_url, decode_responses=True)
    return _client


def reset_redis_client() -> None:
    """Drop the cached client (used by tests)."""
    global _client
    _client = None
