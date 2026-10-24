import time

import httpx

from .base import LLMRequest, LLMResult, LLMUnavailable


class OllamaProvider:
    """Local open-weight models (e.g. Gemma 4) served by Ollama. Used for dev, eval and fallback."""

    name = "ollama"

    def __init__(self, base_url: str, model: str, timeout_s: float = 60.0) -> None:
        self.model = model
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout_s)

    async def generate(self, request: LLMRequest) -> LLMResult:
        messages = []
        if request.system:
            messages.append({"role": "system", "content": request.system})
        messages.append({"role": "user", "content": request.prompt})

        payload: dict = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_output_tokens,
            },
        }
        if request.json_schema is not None:
            payload["format"] = request.json_schema

        start = time.perf_counter()
        try:
            resp = await self._client.post("/api/chat", json=payload)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMUnavailable(f"ollama: {exc}") from exc
        data = resp.json()

        return LLMResult(
            text=data["message"]["content"],
            provider=self.name,
            model=self.model,
            latency_ms=int((time.perf_counter() - start) * 1000),
            input_tokens=data.get("prompt_eval_count"),
            output_tokens=data.get("eval_count"),
        )
