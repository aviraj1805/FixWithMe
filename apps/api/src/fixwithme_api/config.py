from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables (or a local .env file)."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="FWM_", extra="ignore")

    env: Literal["dev", "test", "prod"] = "dev"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # Which LLM backends to try, in order. A rate-limited or unavailable provider falls through
    # to the next one; the diagnostic engine keeps working even if every provider is down.
    llm_chain: list[Literal["gemini", "ollama", "fake"]] = Field(
        default_factory=lambda: ["gemini", "ollama"]
    )

    gemini_api_key: str | None = None
    # Model ids are config, not code: free-tier model availability changes often.
    # Flash-Lite first: on 2026-10-24 it answered in ~1.3 s, while gemini-3.8-flash on the free
    # tier took 90-150 s per call (docs/constraints.md).
    gemini_models: list[str] = Field(
        default_factory=lambda: ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]
    )
    gemini_timeout_s: float = 20.0
    gemini_thinking_level: str | None = "low"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma4:e4b"

    llm_timeout_s: float = 30.0

    # Supabase PostgREST for anonymous outcomes. The publishable key only allows inserts (RLS).
    supabase_url: str | None = None
    supabase_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
