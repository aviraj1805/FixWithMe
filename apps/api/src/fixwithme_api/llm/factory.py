from ..config import Settings
from .base import LLMProvider
from .fake import FakeProvider
from .router import FallbackRouter


def build_llm(settings: Settings) -> FallbackRouter:
    """Builds the provider chain from settings. Unconfigured providers are skipped."""
    providers: list[LLMProvider] = []
    for kind in settings.llm_chain:
        if kind == "gemini":
            if not settings.gemini_api_key:
                continue
            from .gemini import GeminiProvider

            providers.extend(
                GeminiProvider(
                    settings.gemini_api_key,
                    model,
                    timeout_s=settings.gemini_timeout_s,
                    thinking_level=settings.gemini_thinking_level,
                )
                for model in settings.gemini_models
            )
        elif kind == "ollama":
            from .ollama import OllamaProvider

            providers.append(
                OllamaProvider(
                    settings.ollama_base_url, settings.ollama_model, settings.llm_timeout_s
                )
            )
        elif kind == "fake":
            providers.append(FakeProvider())
    if not providers:
        raise ValueError("No LLM provider configured; set FWM_GEMINI_API_KEY or include 'ollama'")
    return FallbackRouter(providers)
