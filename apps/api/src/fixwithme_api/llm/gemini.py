import asyncio
import time

from google import genai
from google.genai import errors, types

from .base import LLMRateLimited, LLMRequest, LLMResult, LLMUnavailable

# The API rejects deadlines shorter than 10 s.
MIN_TIMEOUT_S = 10.0


class GeminiProvider:
    """Google Gemini via the google-genai SDK.

    Free-tier terms: don't send personal data. Callers must run the PII scrubber and the
    on-device image privacy filter before anything reaches this provider (blueprint §8).
    """

    name = "gemini"

    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_s: float = 20.0,
        thinking_level: str | None = None,
    ) -> None:
        self.model = model
        self.timeout_s = max(timeout_s, MIN_TIMEOUT_S)
        self.thinking_level = thinking_level
        self._client = genai.Client(
            api_key=api_key, http_options=types.HttpOptions(timeout=int(self.timeout_s * 1000))
        )

    async def generate(self, request: LLMRequest) -> LLMResult:
        config = types.GenerateContentConfig(
            system_instruction=request.system,
            temperature=request.temperature,
            max_output_tokens=request.max_output_tokens,
        )
        if self.thinking_level:
            config.thinking_config = types.ThinkingConfig(thinking_level=self.thinking_level)
        if request.json_schema is not None:
            config.response_mime_type = "application/json"
            config.response_json_schema = request.json_schema

        start = time.perf_counter()
        try:
            # The server enforces the deadline (504 on expiry); wait_for is a backstop for a
            # connection that hangs before the server can respond.
            resp = await asyncio.wait_for(
                self._client.aio.models.generate_content(
                    model=self.model, contents=request.prompt, config=config
                ),
                timeout=self.timeout_s + 5,
            )
        except TimeoutError as exc:
            raise LLMUnavailable(f"gemini/{self.model}: timed out") from exc
        except errors.APIError as exc:
            if exc.code == 429:
                raise LLMRateLimited(f"gemini/{self.model}: {exc.message}") from exc
            raise LLMUnavailable(f"gemini/{self.model}: {exc.code} {exc.message}") from exc

        usage = resp.usage_metadata
        return LLMResult(
            text=resp.text or "",
            provider=self.name,
            model=self.model,
            latency_ms=int((time.perf_counter() - start) * 1000),
            input_tokens=usage.prompt_token_count if usage else None,
            output_tokens=usage.candidates_token_count if usage else None,
        )
