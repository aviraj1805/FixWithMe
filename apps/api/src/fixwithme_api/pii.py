"""Strips personal data from text before it reaches an LLM (Gemini free-tier terms, DPDP Act)."""

import re

_PHONE = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_URL = re.compile(r"https?://\S+", re.IGNORECASE)


def scrub(text: str) -> str:
    text = _EMAIL.sub("[email]", text)
    text = _URL.sub("[link]", text)
    return _PHONE.sub("[phone]", text)
