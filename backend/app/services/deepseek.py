"""DeepSeek chat client (Phase 11).

A thin, timeout-guarded HTTP client for the DeepSeek chat completions API.
All outbound calls have bounded timeouts.

Errors are raised as ``DeepSeekError`` with a ``transient`` flag:

  - transient=True  -> the call may succeed if retried (timeout, 5xx,
                       network error). The investigation task retries these
                       with backoff.
  - transient=False -> retrying will not help (auth failure, malformed
                       response). The task fails immediately.

Upstream response bodies are never propagated to callers or logs.
"""

from __future__ import annotations

from typing import Optional

import httpx

from app.core.config import Settings


class DeepSeekError(Exception):
    """Raised when the DeepSeek API call or response parsing fails."""

    error_type = "DeepSeekError"

    def __init__(self, message: str, *, transient: bool = False) -> None:
        super().__init__(message)
        self.message = message
        self.transient = transient


class DeepSeekClient:
    """Minimal DeepSeek chat-completions client."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        from app.core.config import get_settings

        self.settings = settings or get_settings()
        self.base_url = self.settings.deepseek_base_url.rstrip("/")
        self.model = self.settings.deepseek_model
        self.api_key = self.settings.deepseek_api_key
        self.timeout = httpx.Timeout(self.settings.deepseek_timeout_seconds)

    def chat_completion(
        self,
        messages: list[dict],
        *,
        response_format: Optional[dict] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Call the chat completions endpoint and return the assistant text."""
        if not self.api_key:
            raise DeepSeekError("DeepSeek API key is not configured")

        payload: dict = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": max_tokens or self.settings.deepseek_max_tokens,
        }
        if response_format is not None:
            payload["response_format"] = response_format

        try:
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise DeepSeekError("DeepSeek request timed out", transient=True) from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            transient = 500 <= status < 600
            raise DeepSeekError(
                f"DeepSeek API returned HTTP {status}", transient=transient
            ) from exc
        except httpx.HTTPError as exc:
            raise DeepSeekError("DeepSeek request failed (network error)", transient=True) from exc

        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise DeepSeekError(
                "Unexpected DeepSeek response shape", transient=False
            ) from exc

        return content
