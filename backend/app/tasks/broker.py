"""Dramatiq broker configuration.

In production the broker is Redis (``REDIS_URL``). Tests install a
StubBroker BEFORE importing application modules, so ``configure_broker``
only applies the Redis broker when none is set yet.
"""

from __future__ import annotations

import dramatiq
from dramatiq.broker import default_middleware
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import CurrentMessage
from dramatiq.middleware.prometheus import Prometheus
from dramatiq.middleware.retries import Retries

from app.core.config import get_settings


def build_redis_broker() -> RedisBroker:
    settings = get_settings()
    # Keep the standard middleware set with two adjustments:
    #  - Prometheus is dropped: metrics are not exposed and the optional
    #    prometheus-client package is not installed.
    #  - CurrentMessage is added so actors can read the current message id.
    #  - Retries is replaced with the project retry policy
    #    (max 3 retries, exponential backoff).
    middleware = [
        m()
        for m in default_middleware
        if m is not Prometheus and m is not Retries
    ]
    middleware.append(CurrentMessage())
    middleware.append(
        Retries(
            max_retries=settings.dramatiq_max_retries,
            min_backoff=settings.dramatiq_min_backoff_ms,
            max_backoff=settings.dramatiq_max_backoff_ms,
        )
    )
    return RedisBroker(url=settings.redis_url, middleware=middleware)


def configure_broker() -> None:
    """Install the Redis broker unless one is already installed (tests)."""
    if dramatiq.broker is not None:
        return
    dramatiq.set_broker(build_redis_broker())


configure_broker()
