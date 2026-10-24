"""Verified answers to free-form questions (R3).

retrieve → draft claims that cite passages (Gemini) → check each claim against its passages
(a different model, Gemma 4) → drop unsupported or unsafe claims → answer, or abstain.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Literal

from .knowledge import Lang
from .llm import FallbackRouter, LLMRequest
from .pii import scrub
from .retrieval import Passage, Retriever

log = logging.getLogger(__name__)

TOP_K = 5

# Instructions we never give, whatever a passage says (blueprint §8, safety levels 2–3 and the
# product-policy exclusions). Matching claims are removed and replaced by a caution.
_UNSAFE = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\b(?:open|remove)\b.{0,25}\b(?:switch\s*board|distribution\s*board|meter|mcb\s*box|consumer\s*unit)\b",
        r"\bbypass\w*\b.{0,25}\b(?:mcb|breaker|fuse|rcd|earth\w*)\b",
        r"\b(?:remove|disconnect|cut)\b.{0,20}\bearth(?:ing)?\b",
        r"\b(?:charge|use)\b.{0,20}\bswollen\b",
        r"\b(?:puncture|pierce)\b.{0,20}\bbatter",
        r"\b(?:touch|hold)\b.{0,25}\blive\b",
        r"\b(?:refrigerant|gas)\b.{0,25}\b(?:refill\w*|recharg\w*|top\s*up)",
        r"\b(?:repair|fix|tighten)\b.{0,25}\b(?:gas\s*pipe|lpg\s*pipe|cylinder\s*valve|regulator\s*valve)\b",
        r"\bwhile\b.{0,20}\b(?:plugged\s*in|switched\s*on|power(?:ed)?\s*on)\b",
    )
]


@dataclass
class Claim:
    text: str
    sources: list[str]
    verdict: Literal["supported", "unsupported", "unchecked"] = "unchecked"


@dataclass
class Answer:
    state: Literal["answer", "abstain"]
    claims: list[Claim] = field(default_factory=list)
    passages: list[Passage] = field(default_factory=list)
    dropped_unsupported: int = 0
    dropped_unsafe: int = 0
    verified: bool = False
    llm_used: bool = False


_DRAFT_SYSTEM = (
    "You answer questions about repairing household items for people in India. Use ONLY the "
    "numbered passages. Write 1 to 4 short, plain claims; each claim must cite the passage ids "
    "that support it. If the passages do not answer the question, set can_answer to false and "
    "return no claims. Never suggest opening switchboards or meters, working on live wires, "
    "bypassing breakers or earthing, repairing gas lines, or charging a swollen battery. "
    "Write the claims in {lang_name}."
)

_VERIFY_SYSTEM = (
    "You check claims against source passages. For each claim, answer supported only if the "
    "cited passages state it or directly imply it; otherwise unsupported. Judge meaning, not "
    "wording; the claim may be in a different language from the passages."
)


def _draft_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "can_answer": {"type": "boolean"},
            "claims": {
                "type": "array",
                "maxItems": 4,
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "sources": {"type": "array", "items": {"type": "string"}, "maxItems": 3},
                    },
                    "required": ["text", "sources"],
                },
            },
        },
        "required": ["can_answer", "claims"],
    }


def _passages_block(passages: list[Passage]) -> str:
    return "\n\n".join(f"[{p.id}] {p.title}\n{p.content}" for p in passages)


_NEGATED = re.compile(
    r"\b(?:do\s*not|don'?t|never|avoid|no|not|nahi|mat)\b[^.;]{0,15}$", re.IGNORECASE
)


def unsafe(text: str) -> bool:
    """True when the text gives a forbidden instruction ("do not charge a swollen battery" is fine)."""
    for p in _UNSAFE:
        for m in p.finditer(text):
            if not _NEGATED.search(text[max(0, m.start() - 25) : m.start()]):
                return True
    return False


async def _draft(
    llm: FallbackRouter, question: str, passages: list[Passage], lang: Lang
) -> list[Claim] | None:
    prompt = f"Passages:\n{_passages_block(passages)}\n\nQuestion: {scrub(question)}"
    system = _DRAFT_SYSTEM.format(lang_name="Hindi (Devanagari)" if lang == "hi" else "English")
    res = await llm.generate(
        LLMRequest(prompt=prompt, system=system, json_schema=_draft_schema(), max_output_tokens=600)
    )
    data = json.loads(res.text)
    if not isinstance(data, dict) or not data.get("can_answer"):
        return []
    valid = {p.id for p in passages}
    claims = []
    for c in data.get("claims") or []:
        text = str(c.get("text", "")).strip()
        srcs = [s for s in c.get("sources") or [] if s in valid]
        if text and srcs:  # a claim without a valid citation is never shown
            claims.append(Claim(text=text, sources=srcs))
    return claims


async def _verify(verifier: FallbackRouter, claims: list[Claim], passages: list[Passage]) -> bool:
    by_id = {p.id: p for p in passages}
    items = []
    for i, c in enumerate(claims):
        cited = "\n".join(f"[{s}] {by_id[s].content}" for s in c.sources)
        items.append(f"Claim {i}: {c.text}\nCited passages:\n{cited}")
    schema = {
        "type": "object",
        "properties": {
            "verdicts": {
                "type": "array",
                "items": {"type": "string", "enum": ["supported", "unsupported"]},
                "minItems": len(claims),
                "maxItems": len(claims),
            }
        },
        "required": ["verdicts"],
    }
    res = await verifier.generate(
        LLMRequest(
            prompt="\n\n".join(items),
            system=_VERIFY_SYSTEM,
            json_schema=schema,
            max_output_tokens=200,
            temperature=0.0,
        )
    )
    verdicts = json.loads(res.text).get("verdicts") or []
    if len(verdicts) != len(claims):
        return False
    for c, v in zip(claims, verdicts, strict=True):
        c.verdict = "supported" if v == "supported" else "unsupported"
    return True


async def answer(
    question: str,
    retriever: Retriever,
    llm: FallbackRouter | None,
    verifier: FallbackRouter | None,
    product: str | None,
    lang: Lang,
) -> Answer:
    # No score cutoff: fused RRF scores are rank-based, not relevance (a keyword-only hit scores at
    # most 1/61). Whether the passages answer the question is the drafter's and verifier's call.
    passages = retriever.search(question, product=product, k=TOP_K)
    if not passages or llm is None:
        return Answer(state="abstain", passages=passages)
    try:
        claims = await _draft(llm, question, passages, lang)
    except Exception as exc:  # LLMError, bad JSON, or a client failure: abstain rather than 500
        log.warning("draft failed: %s", exc)
        return Answer(state="abstain", passages=passages)
    if not claims:
        return Answer(state="abstain", passages=passages, llm_used=True)

    safe = [c for c in claims if not unsafe(c.text)]
    dropped_unsafe = len(claims) - len(safe)

    verified = False
    if verifier is not None and safe:
        try:
            verified = await _verify(verifier, safe, passages)
        except Exception as exc:  # unverified claims are still shown, marked verified=False
            log.warning("verification failed: %s", exc)
    kept = [c for c in safe if c.verdict == "supported"] if verified else safe
    dropped_unsupported = len(safe) - len(kept) if verified else 0
    if not kept:
        return Answer(
            state="abstain",
            passages=passages,
            dropped_unsafe=dropped_unsafe,
            dropped_unsupported=dropped_unsupported,
            verified=verified,
            llm_used=True,
        )
    used = {s for c in kept for s in c.sources}
    return Answer(
        state="answer",
        claims=kept,
        passages=[p for p in passages if p.id in used],
        dropped_unsupported=dropped_unsupported,
        dropped_unsafe=dropped_unsafe,
        verified=verified,
        llm_used=True,
    )
