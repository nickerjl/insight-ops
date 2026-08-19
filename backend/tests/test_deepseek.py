"""DeepSeek client + investigation service tests (Phase 11).

The DeepSeek HTTP call is mocked with respx; no real API key is needed.
Acceptance criteria:
  - relevant evidence is retrieved before the LLM call
  - structured investigation result returned
  - LLM failure handled gracefully
"""

from __future__ import annotations

import httpx
import pytest
import respx

from app.core.config import get_settings
from app.investigation.service import InvestigationResult, run_investigation
from app.investigation.prompt import SYSTEM_PROMPT, build_messages
from app.services.aggregation import record_error_event
from app.services.deepseek import DeepSeekClient, DeepSeekError


def _enable_deepseek(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "deepseek_api_key", "test-key")


def _seed_payment_errors(fake_redis) -> None:
    for _ in range(3):
        record_error_event(
            fake_redis,
            {
                "service": "insightops-api",
                "endpoint": "/api/payments",
                "method": "POST",
                "status_code": 500,
                "error_type": "PaymentProviderTimeout",
                "error_message": "Payment provider timed out",
                "commit_hash": "abc1234",
            },
        )


def test_prompt_contains_only_evidence_and_question():
    messages = build_messages("Why are payments failing?", {"evidence": [{"x": 1}]})
    assert messages[0]["role"] == "system"
    assert "evidence" in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert "Why are payments failing?" in messages[1]["content"]
    assert "Retrieved operational evidence" in messages[1]["content"]


def test_parse_result_validates_structure():
    result = InvestigationResult(
        summary="s",
        likely_cause="c",
        affected_endpoint="/api/payments",
        error_type="PaymentProviderTimeout",
        deployment="abc1234",
        evidence=["e1"],
    )
    assert result.affected_endpoint == "/api/payments"


def test_degraded_result_when_no_api_key(fake_redis):
    _seed_payment_errors(fake_redis)
    outcome = run_investigation("Why are payments failing?")
    assert outcome["status"] == "completed"
    assert "not configured" in outcome["result"]["summary"]
    assert outcome["result"]["deployment"] == "abc1234"


@respx.mock
def test_deepseek_success_returns_structured_result(fake_redis, monkeypatch):
    _enable_deepseek(monkeypatch)
    _seed_payment_errors(fake_redis)

    content = json_dumps_pretty(
        {
            "summary": "Payment failures spiked after deployment abc1234.",
            "likely_cause": "Upstream payment provider timeout.",
            "affected_endpoint": "/api/payments",
            "error_type": "PaymentProviderTimeout",
            "deployment": "abc1234",
            "evidence": ["PaymentProviderTimeout"],
        }
    )
    respx.post("https://api.deepseek.com/chat/completions").mock(
        return_value=httpx.Response(200, json={"choices": [{"message": {"content": content}}]})
    )

    outcome = run_investigation("Why are payment errors increasing?")

    assert outcome["status"] == "completed"
    result = outcome["result"]
    assert result["error_type"] == "PaymentProviderTimeout"
    assert result["affected_endpoint"] == "/api/payments"
    assert result["deployment"] == "abc1234"


@respx.mock
def test_deepseek_http_500_is_transient(fake_redis, monkeypatch):
    """5xx responses are transient: the service re-raises so the task retries."""
    _enable_deepseek(monkeypatch)
    _seed_payment_errors(fake_redis)
    respx.post("https://api.deepseek.com/chat/completions").mock(
        return_value=httpx.Response(500, text="boom")
    )

    with pytest.raises(DeepSeekError) as excinfo:
        run_investigation("Why are payments failing?")
    assert excinfo.value.transient is True


@respx.mock
def test_deepseek_timeout_is_transient(fake_redis, monkeypatch):
    _enable_deepseek(monkeypatch)
    _seed_payment_errors(fake_redis)
    respx.post("https://api.deepseek.com/chat/completions").mock(
        side_effect=httpx.ConnectTimeout("timed out")
    )

    with pytest.raises(DeepSeekError) as excinfo:
        run_investigation("Why are payments failing?")
    assert excinfo.value.transient is True


@respx.mock
def test_deepseek_auth_error_is_non_transient(fake_redis, monkeypatch):
    """4xx auth errors will not succeed on retry -> graceful failed outcome."""
    _enable_deepseek(monkeypatch)
    _seed_payment_errors(fake_redis)
    respx.post("https://api.deepseek.com/chat/completions").mock(
        return_value=httpx.Response(401, text="unauthorized")
    )

    outcome = run_investigation("Why are payments failing?")
    assert outcome["status"] == "failed"
    assert outcome["error"]["type"] == "DeepSeekError"


@respx.mock
def test_deepseek_invalid_json_is_non_transient(fake_redis, monkeypatch):
    _enable_deepseek(monkeypatch)
    _seed_payment_errors(fake_redis)
    respx.post("https://api.deepseek.com/chat/completions").mock(
        return_value=httpx.Response(200, json={"choices": [{"message": {"content": "not json"}}]})
    )

    outcome = run_investigation("Why are payments failing?")
    assert outcome["status"] == "failed"
    assert outcome["error"]["type"] == "DeepSeekError"


def test_client_raises_without_api_key(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "deepseek_api_key", None)
    client = DeepSeekClient(settings)
    with pytest.raises(DeepSeekError):
        client.chat_completion([{"role": "user", "content": "hi"}])


def json_dumps_pretty(data: dict) -> str:
    import json

    return json.dumps(data)
