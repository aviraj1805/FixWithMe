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

    # Verifier for answer claims: a different model family from the drafting model (Gemma 4), with
    # an older Flash-Lite as backup because Gemma returned occasional 500s on 2026-10-24.
    verifier_models: list[str] = Field(
        default_factory=lambda: ["gemma-4-26b-a4b-it", "gemini-3.1-flash-lite"]
    )
    verifier_thinking_level: str | None = "minimal"

    # Tier C web-grounded suggestions. Google Search grounding was free on Gemma 4 but not on
    # Flash-Lite (checked 2026-10-24). Empty list disables it.
    web_models: list[str] = Field(default_factory=lambda: ["gemma-4-26b-a4b-it"])

    # Fixy's voice (Gemini TTS, free on 2026-10-25). The browser voice is the fallback.
    tts_models: list[str] = Field(
        default_factory=lambda: ["gemini-3.8-flash-lite-tts", "gemini-3.1-flash-tts-preview"]
    )
    tts_voice: str = "Despina"  # warm, smooth female voice

    # Retrieval: "supabase" (pgvector + PGroonga RPC), "local" (in-memory from corpus files), "off".
    retrieval: Literal["supabase", "local", "off"] = "supabase"
    retrieval_corpus: str | None = None  # local backend: ingest/corpus.jsonl
    retrieval_embeddings: str | None = None  # local backend: ingest/raw/embeddings.json

    # Per-IP limits on POST /v1/* (protects the shared free Gemini quota). 0 disables.
    rate_per_minute: int = 40  # voice mode adds one /v1/speak call per reply
    rate_per_day: int = 600

    # Supabase PostgREST for anonymous outcomes. The publishable key only allows inserts (RLS).
    supabase_url: str | None = None
    supabase_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
