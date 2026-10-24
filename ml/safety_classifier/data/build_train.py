"""Template-generated training data for FT-1 (7 classes: none + 6 hazards).

Written after the held-out test set and kept separate from it: no test sentence is copied here.
Run: python build_train.py  ->  train_templates.jsonl
"""

import json
import random
from pathlib import Path

random.seed(7)

ITEMS_EN = ["fan", "ceiling fan", "extension board", "power strip", "switch", "switchboard", "socket", "plug", "wire", "cable", "charger", "mixer", "iron", "heater", "kettle", "geyser", "AC", "cooler", "fridge", "washing machine", "TV", "inverter", "motor", "regulator", "laptop", "toy", "remote", "speaker", "trimmer", "induction stove", "microwave", "water pump", "meter"]
ITEMS_HL = ["pankha", "fan", "board", "extension", "switch", "socket", "plug", "taar", "wire", "charger", "mixer", "press", "heater", "geyser", "cooler", "fridge", "machine", "TV", "motor", "regulator", "khilona", "remote", "inverter", "meter"]
ITEMS_DEV = ["पंखा", "बोर्ड", "स्विच", "सॉकेट", "प्लग", "तार", "चार्जर", "मिक्सर", "प्रेस", "हीटर", "गीज़र", "कूलर", "फ्रिज", "मोटर", "खिलौना", "रिमोट", "इन्वर्टर"]
WET_EN = ["switch", "switchboard", "socket", "plug", "extension board", "power strip", "wire", "charger", "MCB", "meter", "adapter", "inverter"]
WET_HL = ["switch", "board", "socket", "plug", "extension", "taar", "wire", "charger", "MCB", "meter"]
WET_DEV = ["स्विच", "बोर्ड", "सॉकेट", "प्लग", "तार", "चार्जर", "मीटर"]
BATT_EN = ["phone", "mobile", "laptop", "power bank", "earbuds case", "smartwatch", "tablet", "drone", "toy car", "trimmer", "bluetooth speaker", "e-bike"]
BATT_HL = ["phone", "mobile", "laptop", "power bank", "earbuds", "watch", "toy car", "trimmer", "speaker"]
BATT_DEV = ["मोबाइल", "फोन", "पावर बैंक", "लैपटॉप", "घड़ी"]
KID_EN = ["baby", "son", "daughter", "toddler", "child", "kid", "little brother", "nephew", "grandson"]
KID_HL = ["baccha", "bachche", "beta", "beti", "chhota bhai", "bachi", "munna", "bitiya"]
KID_DEV = ["बच्चे", "बेटे", "बेटी", "छोटे भाई"]

T = {
    "fire_smoke": {
        "en": ["{i} is smoking", "smoke coming from the {i}", "burning smell from the {i}", "I can smell something burning near the {i}", "sparks from the {i}", "the {i} caught fire", "the {i} is melting", "burn marks on the {i}", "{i} smells burnt", "{i} sparked and went off", "there was a flash and smoke at the {i}", "black marks and a strange smell on the {i}", "the {i} wire is burnt", "fire near the {i}", "the {i} gave off sparks and smoke"],
        "hl": ["{i} se dhuan nikal raha hai", "{i} se jalne ki smell aa rahi hai", "{i} me chingari aayi", "{i} jal gaya", "{i} me aag lag gayi", "{i} pighal gaya", "{i} se jali hui badbu aa rahi", "{i} kaala pad gaya aur badbu aa rahi", "{i} se dhuwa uth raha hai", "{i} me spark hua", "{i} ka taar jal gaya"],
        "dev": ["{i} से धुआं निकल रहा है", "{i} से जलने की गंध आ रही है", "{i} में चिंगारी निकली", "{i} जल गया", "{i} में आग लग गई", "{i} पिघल गया", "{i} से जली हुई बदबू आ रही है", "{i} का तार जल गया"],
    },
    "shock": {
        "en": ["I got a shock from the {i}", "the {i} gives a shock", "the {i} body has current", "touching the {i} gave me a jolt", "felt current in the {i}", "my child got shocked by the {i}", "tingling when I touch the {i}", "electric shock from the {i}", "the {i} is giving current", "someone was electrocuted by the {i}"],
        "hl": ["{i} me current aa raha hai", "{i} chhune par current lagta hai", "{i} se jhatka laga", "{i} ki body me current hai", "{i} ne current maara", "{i} chhua to current laga", "{i} me halka current hai"],
        "dev": ["{i} में करंट आ रहा है", "{i} से झटका लगा", "{i} छूने पर करंट लगता है", "{i} की बॉडी में करंट है"],
    },
    "gas": {
        "en": ["gas smell in the kitchen", "smell of gas near the stove", "LPG leak at home", "the cylinder is leaking gas", "I can smell LPG", "gas is leaking from the pipe", "hissing from the gas cylinder and a smell", "strong gas odour in the house", "smells like gas when I open the kitchen", "possible gas leak near the burner", "the gas pipe is leaking"],
        "hl": ["gas ki smell aa rahi hai", "cylinder se gas leak ho rahi hai", "kitchen me gas ki badbu", "pipe se gas nikal rahi hai", "LPG ki gandh aa rahi hai", "gas leak lag raha hai", "chulhe ke paas gas ki smell"],
        "dev": ["गैस की गंध आ रही है", "सिलेंडर से गैस लीक हो रही है", "रसोई में गैस की बदबू", "पाइप से गैस निकल रही है"],
    },
    "water_electric": {
        "en": ["water fell on the {i}", "the {i} got wet", "water is leaking onto the {i}", "the {i} is sitting in water", "rain water entered the {i}", "water splashed into the {i}", "the {i} is soaked", "water dripping on the {i}"],
        "hl": ["{i} pe paani gir gaya", "{i} geela ho gaya", "{i} me paani chala gaya", "baarish ka paani {i} me aa gaya", "{i} pe pani tapak raha hai"],
        "dev": ["{i} पर पानी गिर गया", "{i} गीला हो गया", "{i} में पानी चला गया", "{i} पर पानी टपक रहा है"],
    },
    "battery_swollen": {
        "en": ["the {i} battery is swollen", "{i} battery is bulging", "the {i} has puffed up", "{i} battery swelled up", "the back of my {i} is pushed out by the battery", "the {i} pack looks bloated", "{i} battery is expanding", "the {i} case is bulging out"],
        "hl": ["{i} ki battery phool gayi", "{i} phool gaya hai", "{i} ki battery fool gayi hai", "{i} ki battery ubhar aayi hai", "{i} ki battery moti ho gayi", "{i} ka back cover battery se uth gaya"],
        "dev": ["{i} की बैटरी फूल गई", "{i} फूल गया है", "{i} की बैटरी उभर आई है"],
    },
    "button_cell": {
        "en": ["my {i} swallowed a battery", "{i} swallowed a coin cell", "I think my {i} ate a button battery", "{i} put a button cell in the mouth and now it's gone", "{i} swallowed a magnet", "{i} may have swallowed the remote battery", "my {i} swallowed a watch battery", "{i} swallowed a small battery from a toy"],
        "hl": ["{i} ne battery nigal li", "{i} ne cell nigal liya", "{i} ne button cell kha liya", "{i} ke munh me battery thi ab nahi mil rahi", "{i} ne magnet nigal liya", "{i} ne remote ka cell nigal liya"],
        "dev": ["{i} ने बैटरी निगल ली", "{i} ने सेल निगल लिया", "{i} ने बटन बैटरी खा ली", "{i} ने चुंबक निगल लिया"],
    },
    "none": {
        "en": ["{i} is not working", "{i} stopped working", "{i} is very slow", "{i} makes a noise", "{i} won't turn on", "the {i} light is off", "the {i} light is on but nothing happens", "only one side of the {i} works", "{i} is not charging", "the {i} battery is low", "I changed the batteries in the {i}", "{i} buttons don't work", "the {i} is loose", "the {i} is a bit warm", "need a new {i}", "how do I clean the {i}", "the {i} keeps switching off", "{i} display is blank", "the {i} hums", "{i} is vibrating", "{i} takes too long", "the {i} cord is short", "{i} knob is broken", "{i} works sometimes", "the {i} is stuck", "{i} remote is lost", "where can I buy a {i}"],
        "hl": ["{i} kaam nahi kar raha", "{i} band ho gaya", "{i} dheere chal raha hai", "{i} se awaaz aa rahi hai", "{i} on nahi hota", "{i} ki light nahi jalti", "{i} ki light jalti hai par chalta nahi", "{i} charge nahi hota", "{i} ki battery khatam", "{i} me nayi battery daali", "{i} ka button kaam nahi karta", "{i} dheela hai", "jaldi theek karna hai {i}", "{i} thoda garam hota hai", "{i} kabhi chalta kabhi nahi", "{i} atak gaya", "{i} ka switch kharab hai", "{i} ki speed kam hai"],
        "dev": ["{i} काम नहीं कर रहा", "{i} बंद हो गया", "{i} धीरे चलता है", "{i} से आवाज़ आती है", "{i} की लाइट नहीं जलती", "{i} की लाइट जलती है पर चलता नहीं", "{i} चार्ज नहीं होता", "{i} की बैटरी खत्म", "{i} जल्दी खराब हो गया", "{i} अटक गया"],
    },
}

ITEMS = {
    "fire_smoke": (ITEMS_EN, ITEMS_HL, ITEMS_DEV),
    "shock": (ITEMS_EN, ITEMS_HL, ITEMS_DEV),
    "gas": ([""], [""], [""]),
    "water_electric": (WET_EN, WET_HL, WET_DEV),
    "battery_swollen": (BATT_EN, BATT_HL, BATT_DEV),
    "button_cell": (KID_EN, KID_HL, KID_DEV),
    "none": (ITEMS_EN + BATT_EN, ITEMS_HL + BATT_HL, ITEMS_DEV + BATT_DEV),
}

PER_CLASS = {"none": 1200}
DEFAULT = 260
PREFIXES = ["", "", "", "help ", "please help, ", "urgent: ", "bhai ", "sir ", "ji "]
SUFFIXES = ["", "", "", " what do I do", " kya karu", " please", "!!", " ?", " क्या करूं"]


def noisy(text: str) -> str:
    """Light, realistic noise: casing, a dropped letter, missing punctuation."""
    if random.random() < 0.3:
        text = text.lower()
    if random.random() < 0.15 and len(text) > 12:
        k = random.randrange(1, len(text) - 1)
        if text[k].isalpha():
            text = text[:k] + text[k + 1 :]
    return text.strip()


def main() -> None:
    rows, seen = [], set()
    for label, langs in T.items():
        target = PER_CLASS.get(label, DEFAULT)
        items = ITEMS[label]
        tries = 0
        count = 0
        while count < target and tries < target * 20:
            tries += 1
            li = random.choice([0, 0, 1, 1, 2])
            lang = ("en", "hl", "dev")[li]
            text = random.choice(langs[lang]).format(i=random.choice(items[li])).strip()
            text = noisy(random.choice(PREFIXES) + text + random.choice(SUFFIXES))
            if text in seen:
                continue
            seen.add(text)
            rows.append({"text": text, "label": label, "source": "template", "lang": lang})
            count += 1
    random.shuffle(rows)
    out = Path(__file__).with_name("train_templates.jsonl")
    with out.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    from collections import Counter

    print(len(rows), "rows", dict(Counter(r["label"] for r in rows)))


if __name__ == "__main__":
    main()
