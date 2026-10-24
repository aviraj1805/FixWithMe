"""Turns a free-text problem description (English, Hindi or Hinglish) into structured answers.

The LLM only identifies the product and maps words to the knowledge base's own question ids;
it never diagnoses. Keyword rules run too, both as a fallback when the LLM is unavailable and
to fill gaps it leaves.
"""

import json
import logging
import re
from dataclasses import dataclass, field

from . import knowledge
from .engine import Answer
from .llm import FallbackRouter, LLMError, LLMRequest
from .pii import scrub

log = logging.getLogger(__name__)

OTHER = "other_item"
UNCLEAR = "unclear"
_I = re.IGNORECASE


def _r(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, _I)


# product -> question id -> [(pattern, answer)]; the first matching pattern wins.
_RULES: dict[str, dict[str, list[tuple[re.Pattern[str], Answer]]]] = {
    "ceiling_fan": {
        "hums": [
            (
                _r(
                    r"\b(?:no sound|silent|totally dead|completely dead|no hum|koi aawaz nahi|awaaz nahi)\b|कोई आवाज़ नहीं"
                ),
                "no",
            ),
            (_r(r"\bhum(?:s|ming|med)?\b|\bghun\s*ghun|गुनगुन|भनभन"), "yes"),
        ],
        "slow": [(_r(r"\bslow(?:ly|er)?\b|\bdh(?:ee|i)m\w*|\bdh(?:ee|i)re\b|धीम|धीरे"), "yes")],
        "noise": [(_r(r"\bgrind\w*|\brattl\w*|\bkhad\s*khad|\bkat\s*kat|खड़खड़|घिस"), "yes")],
        "push_spins": [
            (_r(r"\b(?:jam(?:med)?|stuck|stiff|tight|atak\w*)\b|जाम|अटक"), "no"),
            (
                _r(
                    r"\b(?:spins?|turns?|starts?|ghoomta|ghumta)\b.{0,25}\b(?:push\w*|hand|haath|dhakk\w*)\b"
                ),
                "yes",
            ),
            (
                _r(
                    r"\b(?:push\w*|dhakk\w*)\b.{0,30}\b(?:spins?|turns?|starts?|chal\w*|ghoom\w*|ghum\w*)\b"
                ),
                "yes",
            ),
        ],
        "other_power": [
            (_r(r"\b(?:power cut|no electricity|no power|bijli nahi|light nahi)\b|बिजली नहीं"), "no")
        ],
    },
    "extension_board": {
        "heavy_load": [
            (_r(r"\b(?:heater|iron|press|kettle|geyser|microwave|induction)\b|हीटर|प्रेस"), "yes")
        ],
        "reset_popped": [(_r(r"\b(?:reset|overload)\s*button\b"), "yes")],
        "some_sockets": [
            (_r(r"\bsome\s+(?:sockets?|points?|holes?)\b|\bek\s+socket\b|कुछ सॉकेट"), "yes")
        ],
        "wiggle": [
            (_r(r"\b(?:move|moving|wiggle|hila\w*)\b.{0,25}\b(?:cord|wire|plug|taar)\b"), "yes")
        ],
    },
    "headphones": {
        "wireless": [
            (_r(r"\b(?:wired|aux|3\.5\s*mm)\b"), "no"),
            (_r(r"\b(?:bluetooth|wireless|ear\s*buds?|tws|airpods?|neckband|buds)\b"), "yes"),
        ],
        "one_side": [
            (
                _r(
                    r"\b(?:one\s+(?:side|ear|earbud|bud)|left|right|ek\s+(?:side|taraf|kaan))\b|एक तरफ़?"
                ),
                "yes",
            )
        ],
        "wiggle": [
            (
                _r(
                    r"\b(?:cuts?\s+(?:in\s+and\s+)?out|crackl\w*|on\s+and\s+off|wiggl\w*|bend\w*)\b"
                ),
                "yes",
            )
        ],
        "lint": [(_r(r"\b(?:lint|dust|dirt|dhool|kachra)\b|धूल"), "yes")],
    },
    "battery_toy": {
        "is_remote": [
            (
                _r(
                    r"\bremote\s*(?:control\s*)?(?:wal[aie]\s+|ki\s+|ka\s+)?(?:car|gaadi|gadi|truck|helicopter|plane|drone)\b|\b(?:toy|doll|khilona\w*)\b|खिलौन"
                ),
                "no",
            ),
            (_r(r"\bremote\b|रिमोट"), "yes"),
        ],
        "fresh_tried": [
            (
                _r(
                    r"\b(?:new|fresh|changed?)\s+(?:the\s+)?batter\w*|\bbatter\w*\s+(?:changed|replaced|badal\w*)|\bnayi\s+batter\w*|नई बैटरी"
                ),
                "yes",
            )
        ],
        "crust": [(_r(r"\b(?:corro\w*|crust|white\s+powder|rust\w*|jang)\b|जंग"), "yes")],
    },
}


@dataclass
class Extraction:
    item: str = UNCLEAR  # a product id, OTHER or UNCLEAR
    candidates: list[str] = field(default_factory=list)  # set when several products match
    answers: dict[str, Answer] = field(default_factory=dict)
    llm_used: bool = False


def _rule_item(text: str) -> tuple[str, list[str]]:
    matched, excluded = knowledge.detect(text)
    if len(matched) == 1:
        return matched[0], matched
    if not matched and excluded:
        return OTHER, []
    return UNCLEAR, matched


def _rule_answers(product: str, text: str) -> dict[str, Answer]:
    out: dict[str, Answer] = {}
    for qid, rules in _RULES.get(product, {}).items():
        for pattern, ans in rules:
            if pattern.search(text):
                out[qid] = ans
                break
    return out


def _schema(products: list[str]) -> dict:
    props = {
        f"{p}.{q.id}": {"type": "string", "enum": ["yes", "no", "unknown"]}
        for p in products
        for q in knowledge.load(p).questions
    }
    return {
        "type": "object",
        "properties": {
            "item": {"type": "string", "enum": [*products, OTHER, UNCLEAR]},
            "answers": {"type": "object", "properties": props},
        },
        "required": ["item", "answers"],
    }


_SYSTEM = (
    "You extract facts from a user's description of a broken household item. Users write English, "
    "Hindi or Hinglish. Set item to the matching product id, to other_item if the item is clearly "
    "something not listed (for example a table fan, washing machine or phone), or to unclear. "
    "For each question id of that product, answer yes or no only when the text clearly states it; "
    "otherwise answer unknown. Never guess and never diagnose."
)


def _prompt(products: list[str], text: str) -> str:
    lines = []
    for p in products:
        kb = knowledge.load(p)
        lines.append(f"Product {p} ({kb.names.en}):")
        lines += [f"- {p}.{q.id}: {q.text.en}" for q in kb.questions]
    return "\n".join(lines) + f"\n\nUser text:\n{scrub(text)}"


async def extract(
    text: str, llm: FallbackRouter | None, known_item: str | None = None
) -> Extraction:
    if known_item:
        rules = Extraction(item=known_item, candidates=[known_item])
    else:
        item, candidates = _rule_item(text)
        rules = Extraction(item=item, candidates=candidates)
    if rules.item in knowledge.available():
        rules.answers = _rule_answers(rules.item, text)
    if llm is None:
        return rules

    # Send only the identified product's questions when keywords already settled it: the
    # all-products prompt is several times larger and slower (~5 s vs ~1 s on Flash-Lite).
    settled = known_item or (rules.item if rules.item in knowledge.available() else None)
    products = [settled] if settled else knowledge.available()
    try:
        result = await llm.generate(
            LLMRequest(
                prompt=_prompt(products, text),
                system=_SYSTEM,
                json_schema=_schema(products),
                max_output_tokens=600,
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

    llm_item = data.get("item")
    # Explicit keyword matches win on the item; otherwise trust the LLM within the known products.
    item = rules.item
    if item == UNCLEAR and llm_item in (*products, OTHER):
        item = llm_item
    if item not in knowledge.available():
        return Extraction(item=item, candidates=rules.candidates, llm_used=True)

    valid = {q.id for q in knowledge.load(item).questions}
    llm_answers: dict[str, Answer] = {}
    for key, val in (data.get("answers") or {}).items():
        product, _, qid = str(key).partition(".")
        if product == item and qid in valid and val in ("yes", "no"):
            llm_answers[qid] = val
    answers = {**_rule_answers(item, text), **llm_answers}
    return Extraction(item=item, candidates=[item], answers=answers, llm_used=True)
