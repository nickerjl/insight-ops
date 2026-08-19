"""Logging bootstrap: attach the JSON formatter to the root logger."""

from __future__ import annotations

import logging

from app.core.config import Settings
from app.logging.formatters import JsonFormatter


def setup_logging(settings: Settings) -> None:
    """Configure the root logger to emit structured JSON to stdout."""
    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())

    # Remove pre-existing handlers so configuration is deterministic
    # (important when uvicorn re-invokes app creation in tests).
    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)

    # Keep uvicorn's own access logs quiet; our middleware replaces them.
    for noisy in ("uvicorn.access", "uvicorn.error"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger("app").setLevel(settings.log_level.upper())
