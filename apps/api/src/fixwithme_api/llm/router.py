import dataclasses
import logging
from collections.abc import Sequence

from .base import LLMError, LLMProvider, LLMRequest, LLMResult, LLMUnavailable

log = logging.getLogger(__name__)


class FallbackRouter:
    """Tries providers in order, falling through on rate limits or outages.

    When every provider fails it raises LLMUnavailable; callers then degrade to engine-only mode.
    """

    name = "router"

    def __init__(self, providers: Sequence[LLMProvider]) -> None:
        if not providers:
            raise ValueError("FallbackRouter needs at least one provider")
        self.providers = list(providers)

    async def generate(self, request: LLMRequest) -> LLMResult:
        attempts: list[str] = []
        for provider in self.providers:
            label = f"{provider.name}/{getattr(provider, 'model', '?')}"
            attempts.append(label)
            try:
                result = await provider.generate(request)
            except LLMError as exc:
                log.warning(
                    "llm provider failed, trying next", extra={"provider": label, "error": str(exc)}
                )
                continue
            return dataclasses.replace(result, attempts=tuple(attempts))
        raise LLMUnavailable(f"all LLM providers failed: {', '.join(attempts)}")
