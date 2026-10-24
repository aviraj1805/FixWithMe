"""Tier C: web-grounded suggestions for items outside the curated knowledge (R3).

Gemma 4 with Google Search grounding (on 2026-10-24 the free tier allowed grounding on Gemma but
not on Flash-Lite). Only bullets that the grounding metadata ties to a web source are kept, the
unsafe-instruction filter still applies, and answers are capped at safety level 1 by the prompt
and labelled "AI suggestion, unverified" in the UI. Google's grounding terms require showing the
returned search suggestions, so their HTML is passed through to the client.
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field

from .answer import unsafe
from .knowledge import Lang
from .pii import scrub

log = logging.getLogger(__name__)

# Gemma rejects a system instruction together with the search tool (500), so the rules go in the
# prompt itself.
_PROMPT = """You help people in India with simple checks on a broken household item.
First search the web for this exact problem, then answer only from what the search found.
Rules:
- Give at most 4 bullet points, each one short sentence. No headings, no intro, no closing line.
- Only suggest checks a non-expert can do safely: with the item switched off and unplugged, from
  the outside, without opening any mains-powered casing.
- Never suggest opening appliances, working on wiring, gas, refrigerant, or a swollen battery.
  If the problem needs that, say a technician should check it.
- Write in {lang_name}.

Problem: {question}"""

# Tier C is capped at safety level 1: anything that opens a casing or works on internals is
# level 2+ and only allowed from curated, cited procedures.
_ABOVE_LEVEL_1 = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\b(?:open|dismantle|disassemble|unscrew|take\s+apart|remove)\b.{0,30}"
        r"\b(?:motor|base|casing|case|cover|body|housing|panel|back|board|adapter|charger|appliance|unit)\b",
        r"\b(?:re-?wire|rewiring|solder\w*|splice|strip\s+the\s+wire)",
        r"\b(?:replace|change|swap)\b.{0,20}"
        r"\b(?:fuse|capacitor|wiring|wire|cord|switch|motor|element|thermostat|pcb|circuit)\b",
        r"\b(?:multimeter|continuity\s+test|test\s+the\s+voltage)\b",
    )
]


def above_level_1(text: str) -> bool:
    return unsafe(text) or any(p.search(text) for p in _ABOVE_LEVEL_1)


_BULLET = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")


@dataclass
class WebSource:
    title: str
    url: str


@dataclass
class WebAnswer:
    claims: list[tuple[str, list[int]]] = field(default_factory=list)  # text, source indices
    sources: list[WebSource] = field(default_factory=list)
    search_html: str | None = None
    dropped_unsafe: int = 0
    dropped_ungrounded: int = 0


def _clean(line: str) -> str:
    return _BULLET.sub("", line).replace("**", "").strip()


def parse(
    text: str, supports: list[tuple[str, list[int]]]
) -> tuple[list[tuple[str, list[int]]], int, int]:
    """Split the answer into bullets and attach the grounding sources of the segments inside each."""
    lines = [ln for ln in text.splitlines() if _BULLET.match(ln)] or [
        ln for ln in text.splitlines() if ln.strip()
    ]
    out, ungrounded, dropped_unsafe = [], 0, 0
    for line in lines:
        cited = sorted({i for seg, idx in supports if seg and seg.strip() in line for i in idx})
        clean = _clean(line)
        if not clean:
            continue
        if not cited:
            ungrounded += 1
        elif above_level_1(clean):
            dropped_unsafe += 1
        else:
            out.append((clean, cited))
    return out, ungrounded, dropped_unsafe


class WebAnswerer:
    def __init__(self, api_key: str, models: list[str], timeout_s: float = 45.0) -> None:
        from google import genai
        from google.genai import types

        self.models = models
        self.timeout_s = timeout_s
        self._client = genai.Client(
            api_key=api_key, http_options=types.HttpOptions(timeout=int(timeout_s * 1000))
        )

    async def answer(self, question: str, lang: Lang) -> WebAnswer | None:
        from google.genai import types

        prompt = _PROMPT.format(
            lang_name="Hindi (Devanagari)" if lang == "hi" else "English", question=scrub(question)
        )
        config = types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            thinking_config=types.ThinkingConfig(thinking_level="minimal"),
            temperature=0.2,
        )
        for model in self.models:
            try:
                resp = await asyncio.wait_for(
                    self._client.aio.models.generate_content(
                        model=model, contents=prompt, config=config
                    ),
                    timeout=self.timeout_s + 5,
                )
            except Exception as exc:  # quota, outage or timeout: try the next model, then give up
                log.warning("web answer failed on %s: %s", model, exc)
                continue
            gm = resp.candidates[0].grounding_metadata if resp.candidates else None
            if not gm or not gm.grounding_chunks:
                return None  # an ungrounded reply is never shown
            chunks = [
                WebSource(title=c.web.title or "web", url=c.web.uri)
                for c in gm.grounding_chunks
                if c.web
            ]
            supports = [
                (s.segment.text if s.segment else "", list(s.grounding_chunk_indices or []))
                for s in gm.grounding_supports or []
            ]
            claims, ungrounded, dropped_unsafe = parse(resp.text or "", supports)
            # Renumber to only the sources actually cited.
            used = sorted({i for _, idx in claims for i in idx if i < len(chunks)})
            remap = {old: new for new, old in enumerate(used)}
            claims = [(t, [remap[i] for i in idx if i in remap]) for t, idx in claims]
            html = gm.search_entry_point.rendered_content if gm.search_entry_point else None
            return WebAnswer(
                claims=claims,
                sources=[chunks[i] for i in used],
                search_html=html,
                dropped_unsafe=dropped_unsafe,
                dropped_ungrounded=ungrounded,
            )
        return None
