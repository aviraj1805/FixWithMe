"""Stores anonymous repair outcomes in Supabase (PostgREST). No names, contacts or locations."""

import logging

import httpx

from .config import Settings

log = logging.getLogger(__name__)


class OutcomeStore:
    def __init__(self, settings: Settings) -> None:
        self._enabled = bool(settings.supabase_url and settings.supabase_key)
        self._client = (
            httpx.AsyncClient(
                base_url=f"{settings.supabase_url}/rest/v1",
                headers={
                    "apikey": settings.supabase_key or "",
                    "Authorization": f"Bearer {settings.supabase_key}",
                    "Prefer": "return=minimal",
                },
                timeout=10.0,
            )
            if self._enabled
            else None
        )

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def save(self, row: dict) -> bool:
        if self._client is None:
            return False
        try:
            resp = await self._client.post("/outcomes", json=row)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            log.warning("outcome not stored: %s", exc)
            return False
        return True
