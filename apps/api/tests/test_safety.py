"""Safety gate v1. Release gate: every hard-block phrase must stop the session."""

import pytest

from fixwithme_api import safety

HARD_BLOCK = {
    "fire_smoke": [
        "there is a burning smell from the fan",
        "smell of something burnt",
        "smoke is coming out of the motor",
        "the fan is smoking",
        "I saw sparks near the switch",
        "it's sparking when I switch it on",
        "fire in the regulator",
        "the wire insulation is melting",
        "fan se jalne ki smell aa rahi hai",
        "motor jal gaya lagta hai",
        "regulator jal raha hai",
        "fan me se dhuan nikal raha hai",
        "dhuaan aa raha hai",
        "switch me chingari aayi",
        "board me aag lag gayi",
        "पंखे से जलने की गंध आ रही है",
        "मोटर जल गई है",
        "पंखे से धुआं निकल रहा है",
        "धुएँ की बदबू है",
        "स्विच में चिंगारी निकली",
        "बोर्ड में आग लगी",
        "तार पिघल गया",
    ],
    "shock": [
        "I got a shock from the fan",
        "my son got shocked touching the switch",
        "someone was electrocuted",
        "fan ko chhune par current laga",
        "switch me current maar raha hai",
        "jhatka laga",
        "पंखे में करंट आ रहा है",
        "स्विच से झटका लगा",
    ],
    "gas": [
        "I can smell gas in the kitchen",
        "LPG smell near the stove",
        "gas leak in kitchen",
        "cylinder se gas ki badbu aa rahi hai",
        "रसोई में गैस की बदबू",
    ],
    "water_electric": [
        "water is dripping on the switch board",
        "pani switch board me chala gaya",
        "the socket is wet",
    ],
}

BENIGN = [
    "my ceiling fan hums but won't spin",
    "the fan is very slow",
    "fan makes a rattling noise",
    "jaldi theek karna hai",
    "pankha dheere chal raha hai",
    "पंखा धीमा चल रहा है",
    "मुझे जल्दी ठीक करना है",
    "आगे क्या करूँ?",
    "regulator speed change nahi hoti",
    "the light works but the fan doesn't",
    "it stopped working yesterday",
    "fan wobbles at high speed",
    "capacitor 2.5 uF 440V",
    "the motor feels warm",
    "छत का पंखा बिल्कुल नहीं चल रहा, कोई आवाज़ भी नहीं, बिजली नहीं है",
    "बिजली चली गई है",
    "bijli nahi hai",
    "पानी की टंकी भरी है",
]


@pytest.mark.parametrize(
    ("hazard", "text"), [(h, t) for h, texts in HARD_BLOCK.items() for t in texts]
)
def test_hard_block_phrases_stop(hazard, text):
    assert hazard in safety.check_text(text)


@pytest.mark.parametrize("text", BENIGN)
def test_benign_phrases_pass(text):
    assert safety.check_text(text) == []


def test_every_hazard_has_localised_stop_content():
    for hid in safety.HAZARDS:
        for lang in ("en", "hi"):
            payload = safety.stop_payload(hid, lang)
            assert payload["title"] and len(payload["actions"]) == 3 and payload["call"] == "112"
