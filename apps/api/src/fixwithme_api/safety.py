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

_BATTERY = r"\b(?:batter(?:y|ies)|cells?|coin\s*cells?|magnets?)\b"
_SWALLOW = r"\b(?:swallow\w*|gulp\w*|nigal\w*|kha\s+(?:li|liya|gaya|gayi|liyi))\b"
_SWELL = r"\b(?:swollen|swell\w*|bulg\w*|puff(?:ed|y|ing)?|bloat\w*|phool\w*|fool\s*ga\w*)\b"

# Order matters: the first matching hazard decides the STOP screen, most urgent first.
_RULES: dict[str, list[re.Pattern[str]]] = {
    "button_cell": [
        re.compile(_SWALLOW + r".{0,40}" + _BATTERY, _I),
        re.compile(_BATTERY + r".{0,40}" + _SWALLOW, _I),
        re.compile(r"(?:बैटरी|सेल).{0,30}निगल|निगल.{0,30}(?:बैटरी|सेल)"),
    ],
    "battery_swollen": [
        re.compile(_SWELL + r".{0,30}\bbatter(?:y|ies)\b", _I),
        re.compile(r"\bbatter(?:y|ies)\b.{0,30}" + _SWELL, _I),
        re.compile(r"बैटरी.{0,20}फूल|फूली.{0,20}बैटरी"),
    ],
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
    # ANSES: call emergency services immediately, even without symptoms; say a button battery
    # was swallowed; every minute counts.
    "button_cell": Hazard(
        "button_cell",
        Text(en="Emergency! Get help now.", hi="आपातकाल! तुरंत मदद लें।"),
        (
            Text(
                en="Call 112 now, even with no symptoms", hi="अभी 112 पर कॉल करें, भले कोई लक्षण न हो"
            ),
            Text(en="Say a button battery was swallowed", hi="बताएं कि बटन बैटरी निगली गई है"),
            Text(en="Go to the nearest hospital", hi="सबसे पास के अस्पताल जाएं"),
        ),
    ),
    # University of Reading: never puncture it; stop using and charging it; if it smokes, don't
    # touch it and call the fire service.
    "battery_swollen": Hazard(
        "battery_swollen",
        Text(en="Stop! Swollen battery.", hi="रुकें! बैटरी फूली हुई है।"),
        (
            Text(en="Don't charge or use it", hi="इसे चार्ज या इस्तेमाल न करें"),
            Text(en="Never press or puncture it", hi="इसे कभी दबाएं या छेदें नहीं"),
            Text(en="Smoking? Don't touch it. Call 112", hi="धुआं निकले? न छुएं। 112 पर कॉल करें"),
        ),
    ),
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


# In Hindi and Hinglish a light "jalti hai" when it is on, so "jal..." next to a light word is
# not about burning. These phrases are blanked before the fire rules run.
_LIGHT_ON = [
    re.compile(
        r"\b(?:lights?|bulbs?|leds?|lamps?|indicators?|batti|tubelight)\b(?:\s+\w+){0,2}\s+jal\w*",
        _I,
    ),
    re.compile(r"(?:लाइट|बत्ती|बल्ब|एलईडी)(?:\s+\S+){0,2}\s+जल\S*"),
]


def check_text(text: str) -> list[str]:
    """Return the ids of every hazard the text mentions, in a stable order."""
    fire_text = text
    for pattern in _LIGHT_ON:
        fire_text = pattern.sub(" ", fire_text)
    found = []
    for hid, patterns in _RULES.items():
        subject = fire_text if hid == "fire_smoke" else text
        if any(p.search(subject) for p in patterns):
            found.append(hid)
    return found


def stop_payload(hazard_id: str, lang: Lang) -> dict:
    h = HAZARDS[hazard_id]
    return {
        "hazard": h.id,
        "title": h.title.get(lang),
        "actions": [a.get(lang) for a in h.actions],
        "call": "112",
    }
