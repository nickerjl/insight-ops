"""Investigation orchestration service (Phase 11).

1. retrieve relevant evidence (bounded)
2. build the prompt
3. call DeepSeek (skipped cleanly when no API key is configured)
4. parse + validate the structured result
5. return it for storage by the task

LLM failures never crash the pipeline: the investigation ends in a
"failed" status with a structured error, and the API reports it gracefully.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.investigation.prompt import build_messages
from app.investigation.retrieval import build_evidence_context
from app.services.deepseek import DeepSeekClient, DeepSeekError

logger = logging.getLogger("app.investigation")


class InvestigationResult(BaseModel):
    """Structured output produced by the LLM investigation."""

    summary: str
    likely_cause: str
    affected_endpoint: Optional[str] = None
    error_type: Optional[str] = None
    deployment: Optional[str] = None
    evidence: list[str] = Field(default_factory=list)


def _parse_result(content: str) -> InvestigationResult:
    """Parse the assistant's JSON object into a validated result."""
    text = content.strip()
    # Tolerate markdown code fences some models add.
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise DeepSeekError(f"DeepSeek returned invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise DeepSeekError("DeepSeek returned a non-object JSON value")
    return InvestigationResult.model_validate(data)


def run_investigation(query: str) -> dict:
    """Run the full investigation and return a result payload.

    Returns ``{"status": "completed", "result": {...}}`` on success or
    ``{"status": "failed", "error": {...}}`` on LLM/parse failure.
    """
    settings = get_settings()
    redis = _redis()
    context = build_evidence_context(redis, query)

    if not settings.deepseek_enabled:
        logger.info("DeepSeek not configured; returning degraded investigation")
        return {
            "status": "completed",
            "result": {
                "summary": (
                    "Investigation completed without an LLM: DeepSeek API key "
                    "is not configured (DEEPSEEK_API_KEY). The evidence below "
                    "was retrieved from the aggregation store."
                ),
                "likely_cause": "No LLM analysis available.",
                "affected_endpoint": None,
                "error_type": None,
                "deployment": context.get("deployment"),
                "evidence": [item["fingerprint"] or item["error_type"] for item in context["evidence"]],
            },
        }

    try:
        messages = build_messages(query, context)
        client = DeepSeekClient(settings)
        content = client.chat_completion(
            messages,
            response_format={"type": "json_object"},
        )
        result = _parse_result(content)
        logger.info(
            "investigation completed",
            extra={"query": query[:120], "evidence_items": len(context["evidence"])},
        )
        return {"status": "completed", "result": result.model_dump()}
    except DeepSeekError as exc:
        logger.error(
            "investigation failed",
            extra={"query": query[:120], "error_type": exc.error_type, "error_message": str(exc)},
        )
        return {"status": "failed", "error": {"type": exc.error_type, "message": str(exc)}}
    except Exception as exc:  # defensive: never crash the worker
        logger.error("investigation failed unexpectedly", exc_info=True)
        return {
            "status": "failed",
            "error": {"type": type(exc).__name__, "message": str(exc)[:300]},
        }


def _redis():
    from app.services.redis_client import get_redis

    return get_redis()
