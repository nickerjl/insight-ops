"""Application settings loaded from environment variables / .env file.

Values are read from the process environment first, then from a `.env`
file if present. Secrets (e.g. DEEPSEEK_API_KEY) are never logged and never
committed to source control.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_REDIS_URL = "redis://localhost:6379/0"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- application -----------------------------------------------------
    app_env: str = "dev"
    service_name: str = "insightops-api"
    commit_hash: str = "dev"
    log_level: str = "INFO"
    api_prefix: str = "/api"

    # --- Redis / Dramatiq ------------------------------------------------
    redis_url: str = DEFAULT_REDIS_URL
    dramatiq_max_retries: int = 3
    dramatiq_min_backoff_ms: int = 1000
    dramatiq_max_backoff_ms: int = 30000

    # --- DeepSeek --------------------------------------------------------
    deepseek_api_key: Optional[str] = None
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    deepseek_timeout_seconds: float = 30.0
    deepseek_max_tokens: int = 1024

    # --- CORS ------------------------------------------------------------
    cors_origins: str = "http://localhost:5173,http://localhost:8080"

    # --- error aggregation / retrieval -----------------------------------
    error_aggregation_ttl: int = 86400
    investigation_ttl: int = 3600
    retrieval_max_items: int = 25
    retrieval_max_chars: int = 12000

    @field_validator("cors_origins")
    @classmethod
    def _split_origins(cls, value: str) -> str:
        """Keep the raw string; parse into a list via the `cors_origin_list` property."""
        return value

    @property
    def cors_origin_list(self) -> list:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def deepseek_enabled(self) -> bool:
        return bool(self.deepseek_api_key)

    def validate_runtime(self) -> None:
        """Fail fast on invalid configuration before the server accepts traffic."""
        if self.app_env not in {"dev", "prod"}:
            raise ValueError(f"APP_ENV must be 'dev' or 'prod', got {self.app_env!r}")
        if not self.redis_url.startswith("redis://"):
            raise ValueError("REDIS_URL must start with redis://")
        if self.dramatiq_max_retries < 0:
            raise ValueError("DRAMATIQ_MAX_RETRIES must be >= 0")
        if self.retrieval_max_items < 1 or self.retrieval_max_chars < 1:
            raise ValueError("Retrieval bounds must be positive")


@lru_cache
def get_settings() -> Settings:
    return Settings()
