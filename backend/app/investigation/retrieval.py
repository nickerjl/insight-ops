"""Evidence retrieval (Phase 10).

Retrieves relevant operational evidence for a natural-language investigation
query from the Redis aggregation store and recent error events, ranks it, and
bounds the context size sent to the LLM.

Retrieval is deliberately lightweight: lexical (token-overlap) relevance
boosted by error count and recency. No embedding model or vector index is
used — keeping infrastructure and cost near zero (see PROJECT_PLAN
Architecture Decision Log). The LLM never receives the full log stream.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass

from app.core.config import get_settings
from app.services.aggregation import list_aggregations, list_recent_events

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "of", "to", "in", "on", "for",
    "with", "why", "what", "which", "who", "when", "where", "how", "is",
    "are", "was", "were", "do", "does", "did", "have", "has", "had", "be",
    "been", "it", "its", "at", "by", "from", "up", "down", "about", "into",
    "over", "after", "before", "between", "increase", "increasing",
    "decrease", "decreasing", "caused", "cause", "spike", "latest", "recent",
}

# Minimum token length kept for matching.
_MIN_TOKEN_LEN = 3

# Recency boost window: errors seen within this window get a bonus.
RECENT_WINDOW_SECONDS = 60 * 60


@dataclass
class EvidenceItem:
    """One piece of retrieved evidence (aggregation or raw event)."""

    kind: str  # "aggregation" | "event"
    fingerprint: Optional[str]
    error_type: str
    endpoint: str
    status_code: int
    count: int
    first_seen: Optional[float]
    last_seen: Optional[float]
    commit_hash: Optional[str]
    message: str
    score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "fingerprint": self.fingerprint,
            "error_type": self.error_type,
            "endpoint": self.endpoint,
            "status_code": self.status_code,
            "count": self.count,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "commit_hash": self.commit_hash,
            "message": self.message,
            "score": round(self.score, 4),
        }


def tokenize(text: str) -> list[str]:
    """Lowercase, split into alphanumeric tokens, drop stopwords/short words."""
    import re

    tokens = re.findall(r"[a-z0-9]+", (text or "").lower())
    return [t for t in tokens if t not in STOPWORDS and len(t) >= _MIN_TOKEN_LEN]


def _match(query_tokens: list[str], haystack: str) -> int:
    """Count query tokens that overlap with the haystack (prefix-aware)."""
    haystack_tokens = tokenize(haystack)
    score = 0
    for q in query_tokens:
        for h in haystack_tokens:
            if q == h or h.startswith(q) or q.startswith(h):
                score += 1
                break
    return score


def _to_evidence_item(agg: dict) -> EvidenceItem:
    def _f(key: str, default: Optional[float] = None) -> Optional[float]:
        try:
            return float(agg.get(key, default))
        except (TypeError, ValueError):
            return default

    return EvidenceItem(
        kind="aggregation",
        fingerprint=agg.get("fingerprint"),
        error_type=agg.get("error_type", "UnknownError"),
        endpoint=agg.get("endpoint", ""),
        status_code=int(agg.get("status_code", 500) or 500),
        count=int(agg.get("count", 0) or 0),
        first_seen=_f("first_seen"),
        last_seen=_f("last_seen"),
        commit_hash=agg.get("commit_hash"),
        message=agg.get("message", ""),
    )


def _score_item(item: EvidenceItem, query_tokens: list[str], now: float) -> EvidenceItem:
    haystack = " ".join(
        [item.error_type, item.endpoint, item.message, item.commit_hash or ""]
    )
    keyword_score = _match(query_tokens, haystack)

    # Severity + frequency + recency boosts.
    severity = 2.0 if item.status_code >= 500 else 0.0
    frequency = 0.0 if item.count <= 1 else min(2.0, 1.0 + 0.5 * (item.count - 1))
    recency = 0.0
    if item.last_seen:
        age = max(0.0, now - item.last_seen)
        if age < RECENT_WINDOW_SECONDS:
            recency = 1.0
        elif age < RECENT_WINDOW_SECONDS * 24:
            recency = 0.5

    item.score = float(keyword_score) + severity + frequency + recency
    return item


def retrieve_evidence(redis, query: str) -> list[EvidenceItem]:
    """Retrieve and rank evidence relevant to the query."""
    settings = get_settings()
    now = time.time()
    query_tokens = tokenize(query)

    items: list[EvidenceItem] = []

    for agg in list_aggregations(redis):
        item = _score_item(_to_evidence_item(agg), query_tokens, now)
        if item.score > 0:
            items.append(item)

    # Recent raw events also count as evidence (dedup by fingerprint+message).
    seen = {(e.fingerprint, e.message) for e in items}
    for raw in list_recent_events(redis, limit=settings.retrieval_max_items * 2):
        event_item = EvidenceItem(
            kind="event",
            fingerprint=raw.get("fingerprint"),
            error_type=raw.get("error_type", "UnknownError"),
            endpoint=raw.get("endpoint", ""),
            status_code=int(raw.get("status_code", 500) or 500),
            count=1,
            first_seen=None,
            last_seen=now,
            commit_hash=raw.get("commit_hash"),
            message=raw.get("error_message", ""),
        )
        event_item = _score_item(event_item, query_tokens, now)
        key = (event_item.fingerprint, event_item.message)
        if key in seen:
            continue
        seen.add(key)
        if event_item.score > 0:
            items.append(event_item)

    items.sort(key=lambda item: item.score, reverse=True)
    return items[: settings.retrieval_max_items]


def build_evidence_context(redis, query: str) -> dict:
    """Return a bounded, LLM-ready evidence context for a query."""
    settings = get_settings()
    items = retrieve_evidence(redis, query)
    items = items[: settings.retrieval_max_items]

    evidence = [item.to_dict() for item in items]

    # Deployment context: most frequent commit hash among evidence.
    commits: dict[str, int] = {}
    for item in items:
        if item.commit_hash:
            commits[item.commit_hash] = commits.get(item.commit_hash, 0) + 1
    deployment = max(commits, key=commits.get) if commits else None

    context = {
        "query": query,
        "retrieved_at": time.time(),
        "deployment": deployment,
        "total_errors_aggregated": sum(
            item.count for item in items if item.kind == "aggregation"
        ),
        "evidence": evidence,
    }
    return _truncate_context(context, max_chars=settings.retrieval_max_chars)


def _truncate_context(context: dict, max_chars: int) -> dict:
    """Hard bound on context size: drop evidence beyond the char budget."""
    evidence = list(context.get("evidence", []))
    kept: list[dict] = []
    used = len(json.dumps({k: v for k, v in context.items() if k != "evidence"}, default=str))
    for item in evidence:
        size = len(json.dumps(item, default=str)) + 2
        if used + size > max_chars:
            break
        kept.append(item)
        used += size
    context["evidence"] = kept
    return context
