"""Turns a free-text problem description (English, Hindi or Hinglish) into structured answers.

The LLM only maps words to the knowledge base's own question ids; it never diagnoses. Keyword
rules run too, both as a fallback when the LLM is unavailable and to fill gaps it leaves.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Literal

from .engine import Answer
from .knowledge import ProductKB
from .llm import FallbackRouter, LLMError, LLMRequest
from .pii import scrub

log = logging.getLogger(__name__)

Item = Literal["ceiling_fan", "other_item", "unclear"]
_I = re.IGNORECASE

_OTHER_FAN = re.compile(r"\b(?:table|pedestal|wall|exhaust|tower)\s+fan\b", _I)
_FAN = re.compile(r"\bfans?\b|\bpankh[aeo]\w*|पंख[ाे]", _I)

_RULES: dict[str, list[tuple[re.Pattern[str], Answer]]] = {
    "hums": [
        (
            re.compile(
                r"\b(?:no sound|silent|totally dead|completely dead|no hum|koi aawaz nahi|awaaz nahi)\b|कोई आवाज़ नहीं",
                _I,
            ),
            "no",
        ),
        (re.compile(r"\bhum(?:s|ming|med)?\b|\bghun\s*ghun|गुनगुन|भनभन", _I), "yes"),
    ],
    "slow": [
        (re.compile(r"\bslow(?:ly|er)?\b|\bdh(?:ee|i)m\w*|\bdh(?:ee|i)re\b|धीम|धीरे", _I), "yes")
    ],
    "noise": [(re.compile(r"\bgrind\w*|\brattl\w*|\bkhad\s*khad|\bkat\s*kat|खड़खड़|घिस", _I), "yes")],
    "push_spins": [
        (re.compile(r"\b(?:jam(?:med)?|stuck|stiff|tight|atak\w*)\b|जाम|अटक", _I), "no"),
        (
            re.compile(
                r"\b(?:spins?|turns?|starts?|ghoomta|ghumta)\b.{0,25}\b(?:push\w*|hand|haath|dhakk\w*)\b",
                _I,
            ),
            "yes",
        ),
        (
            re.compile(
                r"\b(?:push\w*|dhakk\w*)\b.{0,30}\b(?:spins?|turns?|starts?|chal\w*|ghoom\w*|ghum\w*)\b",
                _I,
            ),
            "yes",
        ),
    ],
    "other_power": [
        (
            re.compile(
                r"\b(?:power cut|no electricity|no power|bijli nahi|light nahi)\b|बिजली नहीं", _I
            ),
            "no",
        )
    ],
}


@dataclass
class Extraction:
    item: Item = "unclear"
    answers: dict[str, Answer] = field(default_factory=dict)
    llm_used: bool = False


def _rule_item(text: str) -> Item:
    if _OTHER_FAN.search(text):
        return "other_item"
    return "ceiling_fan" if _FAN.search(text) else "unclear"


def _rule_answers(text: str) -> dict[str, Answer]:
    out: dict[str, Answer] = {}
    for qid, rules in _RULES.items():
        for pattern, ans in rules:
            if pattern.search(text):
                out[qid] = ans
                break
    return out


def _schema(kb: ProductKB) -> dict:
    return {
        "type": "object",
        "properties": {
            "item": {"type": "string", "enum": ["ceiling_fan", "other_item", "unclear"]},
            "answers": {
                "type": "object",
                "properties": {
                    q.id: {"type": "string", "enum": ["yes", "no", "unknown"]} for q in kb.questions
                },
            },
        },
        "required": ["item", "answers"],
    }


_SYSTEM = (
    "You extract facts from a user's description of a broken household item. Users write English, "
    "Hindi or Hinglish. Set item to ceiling_fan if they describe a ceiling fan (pankha), other_item if "
    "it is clearly something else (including table or exhaust fans), and unclear otherwise. For each "
    "question id, answer yes or no only when the text clearly states it; otherwise answer unknown. "
    "Never guess and never diagnose."
)


async def extract(text: str, kb: ProductKB, llm: FallbackRouter | None) -> Extraction:
    rules = Extraction(item=_rule_item(text), answers=_rule_answers(text))
    if llm is None:
        return rules
    questions = "\n".join(f"- {q.id}: {q.text.en}" for q in kb.questions)
    prompt = f"Questions:\n{questions}\n\nUser text:\n{scrub(text)}"
    try:
        result = await llm.generate(
            LLMRequest(
                prompt=prompt, system=_SYSTEM, json_schema=_schema(kb), max_output_tokens=400
            )
        )
        data = json.loads(result.text)
    except (LLMError, json.JSONDecodeError) as exc:
        log.warning("extractor fell back to rules: %s", exc)
        return rules
    except Exception:
        # A failing LLM must never break a diagnosis: the engine works on rule answers alone.
        log.exception("unexpected LLM error; extractor fell back to rules")
        return rules
    if not isinstance(data, dict):
        return rules

    valid_ids = {q.id for q in kb.questions}
    llm_answers: dict[str, Answer] = {
        k: v
        for k, v in (data.get("answers") or {}).items()
        if k in valid_ids and v in ("yes", "no")
    }
    item = (
        data.get("item")
        if data.get("item") in ("ceiling_fan", "other_item", "unclear")
        else "unclear"
    )
    # Keyword rules win on the item only when they are explicit; LLM answers win over rules.
    merged_item = rules.item if rules.item != "unclear" else item
    return Extraction(item=merged_item, answers={**rules.answers, **llm_answers}, llm_used=True)
