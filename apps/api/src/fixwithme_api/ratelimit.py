"""Per-IP request limits for the POST endpoints. In memory: the API runs as one instance, and
the limits exist to protect the shared free Gemini quota from one heavy user."""

import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimit(BaseHTTPMiddleware):
    def __init__(self, app, per_minute: int, per_day: int) -> None:
        super().__init__(app)
        self.limits = ((60.0, per_minute), (86400.0, per_day))
        self.hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        if request.method != "POST" or not request.url.path.startswith("/v1/"):
            return await call_next(request)
        # Render puts the client address first in X-Forwarded-For.
        ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
            request.client.host if request.client else "unknown"
        )
        now = time.monotonic()
        hits = self.hits[ip]
        while hits and now - hits[0] > 86400:
            hits.popleft()
        for window, limit in self.limits:
            if sum(1 for t in hits if now - t <= window) >= limit:
                return JSONResponse(
                    {"detail": "Too many requests. Please try again later."},
                    status_code=429,
                    headers={"Retry-After": str(int(window if window < 3600 else 3600))},
                )
        hits.append(now)
        if len(self.hits) > 50_000:  # bound memory: drop the oldest clients
            for key in list(self.hits)[:10_000]:
                del self.hits[key]
        return await call_next(request)
