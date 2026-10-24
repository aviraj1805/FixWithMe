import asyncio

import pytest

from fixwithme_api.config import Settings
from fixwithme_api.llm import (
    FallbackRouter,
    LLMRateLimited,
    LLMRequest,
    LLMResult,
    LLMUnavailable,
    build_llm,
)
from fixwithme_api.llm.fake import FakeProvider


class FailingProvider:
    def __init__(self, name: str, exc: Exception) -> None:
        self.name = name
        self.model = "m"
        self.exc = exc
        self.calls = 0

    async def generate(self, request: LLMRequest) -> LLMResult:
        self.calls += 1
        raise self.exc


def run(coro):
    return asyncio.run(coro)


def test_router_falls_through_rate_limit_to_next_provider():
    limited = FailingProvider("gemini", LLMRateLimited("429"))
    backup = FakeProvider(reply="from backup")
    router = FallbackRouter([limited, backup])

    result = run(router.generate(LLMRequest(prompt="hi")))

    assert result.text == "from backup"
    assert result.provider == "fake"
    assert result.attempts == ("gemini/m", "fake/fake-1")
    assert limited.calls == 1


def test_router_raises_unavailable_when_all_providers_fail():
    router = FallbackRouter(
        [FailingProvider("a", LLMRateLimited("429")), FailingProvider("b", LLMUnavailable("down"))]
    )

    with pytest.raises(LLMUnavailable, match="all LLM providers failed"):
        run(router.generate(LLMRequest(prompt="hi")))


def test_router_does_not_swallow_programming_errors():
    router = FallbackRouter([FailingProvider("a", KeyError("bug")), FakeProvider()])

    with pytest.raises(KeyError):
        run(router.generate(LLMRequest(prompt="hi")))


def test_build_llm_skips_gemini_without_key():
    router = build_llm(Settings(llm_chain=["gemini", "fake"], gemini_api_key=None))

    assert [p.name for p in router.providers] == ["fake"]


def test_build_llm_expands_one_gemini_provider_per_model():
    settings = Settings(
        llm_chain=["gemini"], gemini_api_key="test-key", gemini_models=["model-a", "model-b"]
    )

    router = build_llm(settings)

    assert [(p.name, p.model) for p in router.providers] == [
        ("gemini", "model-a"),
        ("gemini", "model-b"),
    ]


def test_build_llm_requires_at_least_one_provider():
    with pytest.raises(ValueError, match="No LLM provider configured"):
        build_llm(Settings(llm_chain=["gemini"], gemini_api_key=None))


def test_build_llm_passes_gemini_timeout_and_thinking_with_server_minimum():
    settings = Settings(
        llm_chain=["gemini"],
        gemini_api_key="test-key",
        gemini_models=["model-a"],
        gemini_timeout_s=3,
        gemini_thinking_level="low",
    )

    (provider,) = build_llm(settings).providers

    assert provider.timeout_s == 10.0  # the API rejects deadlines under 10 s
    assert provider.thinking_level == "low"
