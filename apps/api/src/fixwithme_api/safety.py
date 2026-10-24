"""Deterministic safety gate (v1).

Runs on every piece of user text before anything else, and does not depend on an LLM.
It is deliberately biased towards stopping: a false alarm costs one tap, a miss could cost
much more. FT-1 (a fine-tuned classifier) will add recall on top of these rules in R2.
"""

import re
from dataclasses import dataclass

from .knowledge import Lang, Text


@dataclass(frozen=True)
class Hazard:
    id: str
    title: Text
    actions: tuple[Text, ...]


_I = re.IGNORECASE

_WS = r"(?<![ऀ-ॿ])"  # start of a Devanagari word

_RULES: dict[str, list[re.Pattern[str]]] = {
    "fire_smoke": [
        re.compile(r"\bburn(?:ing|t|s|ed)?\b", _I),
        re.compile(r"\bsmok(?:e|ing|ey|y)\b", _I),
        re.compile(r"\b(?:fire|flames?|sparks?|sparking)\b", _I),
        re.compile(r"\bmelt(?:ing|ed|s)?\b", _I),
        # Hinglish. Bare "jal" means water, so only verb forms count.
        re.compile(r"\bjal(?:a|i|e|ne|na|ta|ti|raha|rahi|rha|rhi|gaya|gayi|gya|gyi)\b", _I),
        re.compile(
            r"\bjal\s+(?:gaya|gayi|gya|gyi|raha|rahi|rha|rhi|chuka|chuki|jaye|jayega)\b", _I
        ),
        re.compile(r"\bdhu+w?a+n?\b", _I),
        re.compile(r"\b(?:chingaa?ri|aag|pighal\w*)\b", _I),
        # Devanagari has no \b, so _WS marks a word start. Without it "बिजली" (electricity)
        # matches "जली" (burnt). "जल्दी" (quickly) is excluded by requiring a vowel sign.
        re.compile(_WS + r"(?:जल[ाीेु]|जलने|जल\s?(?:रह|गय|गई|गयी|चुक))"),
        re.compile(_WS + r"(?:धु[आएं]|धुँ)"),
        # "आग" (fire) but not "आगे" (ahead): no Devanagari letter may follow.
        re.compile(_WS + r"(?:चिंगारी|आग(?![ऀ-ॿ])|पिघल)"),
    ],
    "shock": [
        re.compile(r"\bshock(?:ed|s)?\b", _I),
        re.compile(r"\belectrocut\w*", _I),
        re.compile(
            r"\bcurrent\s+(?:laga|lag|lagta|lagti|lagi|maar\w*|mara|aa\s+raha|aata|aati)\b", _I
        ),
        re.compile(r"\bjhatk(?:a|e)\b", _I),
        re.compile(_WS + r"(?:करंट|झटका)"),
    ],
    "gas": [
        re.compile(r"\b(?:gas|lpg|cylinder)\b.{0,25}\b(?:smell\w*|leak\w*|badbu|gandh)\b", _I),
        re.compile(r"\b(?:smell\w*|leak\w*|badbu|gandh)\b.{0,25}\b(?:gas|lpg|cylinder)\b", _I),
        re.compile(r"गैस.{0,15}(?:गंध|बदबू|लीक)|(?:गंध|बदबू|लीक).{0,15}गैस"),
    ],
    "water_electric": [
        re.compile(
            r"\b(?:water|paani|pani|wet)\b.{0,30}\b(?:switch\w*|socket|board|wire\w*|plug|mcb)\b",
            _I,
        ),
        re.compile(
            r"\b(?:switch\w*|socket|board|wire\w*|plug|mcb)\b.{0,30}\b(?:water|paani|pani|wet)\b",
            _I,
        ),
    ],
}

_CALL = Text(en="Smoke, fire or someone hurt? Call 112", hi="धुआं, आग या कोई घायल? 112 पर कॉल करें")
HAZARDS: dict[str, Hazard] = {
    "fire_smoke": Hazard(
        "fire_smoke",
        Text(en="Stop! Power off.", hi="रुकें! बिजली बंद करें।"),
        (
            Text(en="Switch off the MCB", hi="MCB बंद करें"),
            Text(en="Don't touch it", hi="इसे न छुएं"),
            _CALL,
        ),
    ),
    "shock": Hazard(
        "shock",
        Text(en="Stop! Don't touch it.", hi="रुकें! इसे न छुएं।"),
        (
            Text(en="Switch off the MCB", hi="MCB बंद करें"),
            Text(en="Keep everyone away", hi="सबको दूर रखें"),
            _CALL,
        ),
    ),
    "gas": Hazard(
        "gas",
        Text(en="Stop! Possible gas leak.", hi="रुकें! गैस लीक हो सकती है।"),
        (
            Text(en="Don't touch any switch", hi="कोई स्विच न छुएं"),
            Text(en="Open windows, close the cylinder", hi="खिड़कियां खोलें, सिलेंडर बंद करें"),
            Text(en="Leave and call 112", hi="बाहर जाएं और 112 पर कॉल करें"),
        ),
    ),
    "water_electric": Hazard(
        "water_electric",
        Text(en="Stop! Water and power.", hi="रुकें! पानी और बिजली।"),
        (
            Text(en="Switch off the MCB, if your hands are dry", hi="हाथ सूखे हों तो MCB बंद करें"),
            Text(en="Don't touch anything wet", hi="गीली चीज़ न छुएं"),
            _CALL,
        ),
    ),
}


def check_text(text: str) -> list[str]:
    """Return the ids of every hazard the text mentions, in a stable order."""
    return [hid for hid, patterns in _RULES.items() if any(p.search(text) for p in patterns)]


def stop_payload(hazard_id: str, lang: Lang) -> dict:
    h = HAZARDS[hazard_id]
    return {
        "hazard": h.id,
        "title": h.title.get(lang),
        "actions": [a.get(lang) for a in h.actions],
        "call": "112",
    }
