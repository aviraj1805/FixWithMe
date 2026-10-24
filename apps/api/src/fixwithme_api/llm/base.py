from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class LLMRequest:
    prompt: str
    system: str | None = None
    # When set, the provider must return JSON matching this JSON Schema.
    json_schema: dict[str, Any] | None = None
    temperature: float = 0.2
    max_output_tokens: int = 1024


@dataclass(frozen=True)
class LLMResult:
    text: str
    provider: str
    model: str
    latency_ms: int
    input_tokens: int | None = None
    output_tokens: int | None = None
    attempts: tuple[str, ...] = field(default_factory=tuple)


class LLMError(Exception):
    """Base error for LLM providers."""


class LLMRateLimited(LLMError):
    """Quota or rate limit hit; the caller should try another provider or back off."""


class LLMUnavailable(LLMError):
    """Provider is not configured, unreachable, or returned a server error."""


class LLMProvider(Protocol):
    name: str

    async def generate(self, request: LLMRequest) -> LLMResult: ...
