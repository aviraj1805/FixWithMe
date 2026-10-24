from .base import LLMRequest, LLMResult


class FakeProvider:
    """Deterministic provider for tests and offline development."""

    name = "fake"

    def __init__(self, reply: str = "ok", model: str = "fake-1") -> None:
        self.reply = reply
        self.model = model
        self.calls: list[LLMRequest] = []

    async def generate(self, request: LLMRequest) -> LLMResult:
        self.calls.append(request)
        return LLMResult(text=self.reply, provider=self.name, model=self.model, latency_ms=0)
