"""Prompt construction for DeepSeek investigations (Phase 11).

The LLM receives only the bounded, pre-retrieved evidence — never the full
log stream — and is asked to return a structured JSON object.
"""

from __future__ import annotations

import json

SYSTEM_PROMPT = (
    "You are InsightOps, an expert site-reliability engineer assistant. "
    "You analyze operational evidence (error aggregations, endpoints, counts, "
    "deployments) to help developers investigate production incidents. "
    "Answer only based on the provided evidence. "
    'Always reply with a single valid JSON object with exactly these keys: '
    '"summary", "likely_cause", "affected_endpoint", "error_type", '
    '"deployment", "evidence". "evidence" is an array of strings referencing '
    "the evidence items you used. Do not include text outside the JSON object."
)


def build_messages(query: str, context: dict) -> list[dict]:
    """Build the chat messages for the DeepSeek API."""
    evidence_text = json.dumps(context, indent=2, default=str)
    user_prompt = (
        "Investigation question: "
        f"{query}\n\n"
        "Retrieved operational evidence (JSON):\n"
        f"{evidence_text}\n\n"
        "Analyze the evidence and answer the question. "
        "If the evidence does not contain enough information, say so in "
        '"summary" instead of guessing.'
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
