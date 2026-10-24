"""Paraphrase augmentation for FT-1 with Gemma 4 (via the Gemini API free tier, its own quota).

Prompts describe each class in general terms and never show held-out test sentences.
Output: train_gemma.jsonl (label, text, source="gemma"). Run from repo root with the API venv.
"""

import asyncio
import json
import random
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "apps" / "api" / "src"))
from fixwithme_api.config import Settings  # noqa: E402
from fixwithme_api.llm import LLMRequest  # noqa: E402
from fixwithme_api.llm.gemini import GeminiProvider  # noqa: E402

MODEL = "gemma-4-26b-a4b-it"
INTERVAL_S = 4.2
PER_CALL = 25

CLASSES = {
    "fire_smoke": "something electrical is burning, smoking, sparking, melting, scorched, or on fire",
    "shock": "a person got an electric shock or feels current/tingling when touching an appliance or switch",
    "gas": "a cooking gas (LPG/PNG) smell or leak at home",
    "water_electric": "water has got onto or into a switch, socket, plug, extension board, wiring, charger or meter",
    "battery_swollen": "a rechargeable battery (phone, laptop, power bank, earbuds, toy) is swollen, bulging or puffed up",
    "button_cell": "a young child may have swallowed a battery, coin cell or magnet",
    "none": (
        "an ordinary, non-dangerous problem with a household item (fan, extension board, earphones, "
        "toys, remotes, appliances): not working, slow, noisy, no sound, buttons, batteries flat, "
        "charging, pairing, lights. Include some messages that use alarming-sounding words in a "
        "harmless way, such as brand or product names, normal warmth, low battery, or appliances "
        "that use water working normally"
    ),
}
STYLES = {
    "en": "in Indian English, casual, like a WhatsApp message, some with typos",
    "hinglish": "in Hinglish (Hindi written in Latin letters mixed with English), casual, some with typos",
    "hi": "in Hindi written in Devanagari script, natural everyday words",
}
CALLS = {"none": 4}  # calls per language; hazards get 2


def prompt(desc: str, style: str) -> str:
    return (
        f"Write {PER_CALL} different short messages that a person in India might send to a home-repair "
        f"helper app, where the situation is: {desc}. Write them {style}. Vary the item, wording, length "
        "and sentence structure; don't repeat patterns. One message per line. No numbering, no quotes, "
        "no extra text."
    )


async def main() -> None:
    key = Settings(_env_file=ROOT / "apps" / "api" / ".env").gemini_api_key
    if not key:
        sys.exit("No Gemini key in apps/api/.env")
    llm = GeminiProvider(key, MODEL, timeout_s=60, thinking_level="minimal")  # Gemma 4 thinks by default
    out = HERE / "train_gemma.jsonl"
    test = {json.loads(l)["text"].strip().lower() for l in (HERE / "test_handwritten.jsonl").open(encoding="utf-8")}
    rows, seen, last = [], set(), 0.0
    for label, desc in CLASSES.items():
        for lang, style in STYLES.items():
            for _ in range(CALLS.get(label, 2)):
                wait = last + INTERVAL_S - time.monotonic()
                if wait > 0:
                    await asyncio.sleep(wait)
                last = time.monotonic()
                try:
                    res = await llm.generate(LLMRequest(prompt=prompt(desc, style), temperature=1.0, max_output_tokens=1500))
                except Exception as exc:
                    print(f"  {label}/{lang}: {exc}", flush=True)
                    continue
                added = 0
                for line in res.text.splitlines():
                    text = line.strip().strip("-*•\"'").strip()
                    if len(text) < 6 or len(text) > 200 or text.lower() in seen or text.lower() in test:
                        continue
                    seen.add(text.lower())
                    rows.append({"text": text, "label": label, "source": "gemma", "lang": lang})
                    added += 1
                print(f"{label}/{lang}: +{added}", flush=True)
    random.Random(7).shuffle(rows)
    with out.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(len(rows), "rows ->", out.name)


if __name__ == "__main__":
    asyncio.run(main())
