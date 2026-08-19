"""Error fingerprinting.

Recurring errors get a stable fingerprint derived from stable identifying
information (service, endpoint, exception type, normalized message) so that
repeated occurrences can be grouped instead of being treated as unrelated
errors. Dynamic values (UUIDs, numbers, timestamps) are normalized before
hashing so they do not fragment fingerprints unnecessarily.

    payment-api:/api/payments:PaymentProviderTimeout:<normalized message>
        -> sha256(...).hexdigest()[:20]
"""

from __future__ import annotations

import hashlib
import re

_UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE)
_HEX_RE = re.compile(r"\b[0-9a-f]{8,}\b", re.IGNORECASE)
_INT_RE = re.compile(r"\b\d+\b")
_QUOTED_RE = re.compile(r"""(['"])(.*?)\1""")
_WS_RE = re.compile(r"\s+")

# Path segments that are dynamic identifiers (numeric ids, UUIDs, long hex).
_PATH_UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE)
_PATH_HEX_RE = re.compile(r"^[0-9a-f]{8,}$", re.IGNORECASE)
_PATH_INT_RE = re.compile(r"^\d+$")


def _normalize_path_segment(segment: str) -> str:
    if not segment:
        return segment
    if _PATH_UUID_RE.fullmatch(segment):
        return "<uuid>"
    if _PATH_INT_RE.fullmatch(segment):
        return "<id>"
    if _PATH_HEX_RE.fullmatch(segment):
        return "<hex>"
    return segment


def normalize_endpoint(endpoint: str) -> str:
    """Replace dynamic path segments (ids, uuids, hex) with placeholders.

    ``/api/orders/12345`` and ``/api/orders/67890`` describe the same error
    class and must produce the same fingerprint.
    """
    if not endpoint:
        return endpoint
    parts = endpoint.split("/")
    normalized = [_normalize_path_segment(part) for part in parts]
    return "/".join(normalized)


def normalize_message(message: str) -> str:
    """Normalize dynamic values out of an error message.

    - lowercase
    - quoted values -> '<value>'
    - UUIDs -> '<uuid>'
    - long hex strings -> '<hex>'
    - integers -> '<n>'
    - collapse whitespace
    """
    if not message:
        return ""
    normalized = message.strip().lower()
    normalized = _QUOTED_RE.sub("'<value>'", normalized)
    normalized = _UUID_RE.sub("<uuid>", normalized)
    normalized = _HEX_RE.sub("<hex>", normalized)
    normalized = _INT_RE.sub("<n>", normalized)
    return _WS_RE.sub(" ", normalized)


def build_aggregation_key(
    *,
    service: str,
    endpoint: str,
    exception_type: str,
    message: str,
) -> str:
    """Stable key identifying an error class, independent of occurrence count."""
    return ":".join(
        [
            service or "unknown-service",
            normalize_endpoint(endpoint or "unknown-endpoint"),
            exception_type or "UnknownError",
            normalize_message(message),
        ]
    )


def fingerprint(aggregate_key: str) -> str:
    """Stable 20-char fingerprint for an aggregation key."""
    return hashlib.sha256(aggregate_key.encode("utf-8")).hexdigest()[:20]


def build_fingerprint(
    *,
    service: str,
    endpoint: str,
    exception_type: str,
    message: str,
) -> str:
    return fingerprint(
        build_aggregation_key(
            service=service,
            endpoint=endpoint,
            exception_type=exception_type,
            message=message,
        )
    )
