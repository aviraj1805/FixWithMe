"""Retrieval evaluation: Recall@1, Recall@5 and MRR@10 for vector, keyword and hybrid search.

A retrieved passage is relevant when its id or title starts with one of the query's
`relevant` prefixes. Queries were written by the project author (EN, Hinglish, Hindi).

Usage (repo root, API venv):
  apps/api/.venv/Scripts/python eval/retrieval/run.py [--backend local|supabase]
"""

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "api" / "src"))
from fixwithme_api.config import Settings  # noqa: E402
from fixwithme_api.retrieval import Embedder, LocalBackend, Retriever, SupabaseBackend  # noqa: E402

F, E, H, T, G = "ceiling_fan", "extension_board", "headphones", "battery_toy", None
KB = "kb:"
QUERIES = [
    ("en", F, "what does the capacitor do in a ceiling fan", ["Motor capacitor", "Ceiling fan", "Capacitor", f"{KB}ceiling_fan:cause:capacitor_weak", f"{KB}ceiling_fan:procedure:replace_capacitor"]),
    ("hinglish", F, "pankha hum karta hai par ghoomta nahi kya kharab hai", [f"{KB}ceiling_fan:cause:capacitor_weak", f"{KB}ceiling_fan:procedure:replace_capacitor", "Ceiling fan", "Motor capacitor"]),
    ("en", F, "how to replace fan capacitor safely", [f"{KB}ceiling_fan:procedure:replace_capacitor"]),
    ("en", F, "can I use a 3.15 uF capacitor instead of 2.5 uF", ["Motor capacitor", f"{KB}ceiling_fan:procedure:replace_capacitor", f"{KB}ceiling_fan:cause:capacitor_weak", "Capacitor"]),
    ("hi", F, "पंखे का कैपेसिटर कैसे बदलें", [f"{KB}ceiling_fan:procedure:replace_capacitor", f"{KB}ceiling_fan:cause:capacitor_weak"]),
    ("en", F, "why does my fan make a grinding noise", [f"{KB}ceiling_fan:cause:bearing_stiff", f"{KB}ceiling_fan:procedure:refer_bearing", "Ceiling fan"]),
    ("en", F, "fan regulator speed not changing", [f"{KB}ceiling_fan:cause:regulator_faulty", f"{KB}ceiling_fan:procedure:check_regulator", "Ceiling fan"]),
    ("en", F, "how does a single phase induction motor start", ["Induction motor", "Motor capacitor"]),
    ("en", F, "why is a capacitor dangerous after the power is off", ["Capacitor", f"{KB}ceiling_fan:procedure:replace_capacitor"]),
    ("hi", F, "संधारित्र क्या होता है", ["संधारित्र", "Capacitor"]),
    ("en", E, "what does the reset button on a power strip do", ["Power strip", "Circuit breaker", f"{KB}extension_board:cause:overload_tripped", f"{KB}extension_board:procedure:reset_overload"]),
    ("hinglish", E, "board me heater lagane se band ho gaya", [f"{KB}extension_board:cause:overload_tripped", f"{KB}extension_board:procedure:reset_overload", "Power strip"]),
    ("en", E, "is it safe to plug one extension board into another", ["Power strip", "Extension cord", f"{KB}extension_board:procedure:reset_overload", f"{KB}extension_board:procedure:replace_board"]),
    ("en", E, "extension cord getting hot", ["Extension cord", "Power strip", f"{KB}extension_board:procedure:replace_board"]),
    ("en", E, "difference between MCB and RCD", ["Residual-current device", "Circuit breaker"]),
    ("en", E, "what plug type is used in India", ["AC power plugs and sockets"]),
    ("en", E, "how does a fuse protect a circuit", ["Fuse (electrical)"]),
    ("hi", E, "सर्किट ब्रेकर क्या करता है", ["परिपथ विच्छेदक", "Circuit breaker"]),
    ("en", H, "one side of my earphones is not working", [f"{KB}headphones:", "Headphones"]),
    ("en", H, "how to reset tws earbuds", [f"{KB}headphones:procedure:reset_earbuds", f"{KB}headphones:cause:pairing_glitch"]),
    ("en", H, "what is the difference between TRS and TRRS jacks", ["Phone connector (audio)"]),
    ("en", H, "earbud not charging in the case", [f"{KB}headphones:procedure:clean_contacts_charge", f"{KB}headphones:cause:not_charging"]),
    ("en", H, "how does bluetooth pairing work", ["Bluetooth"]),
    ("en", H, "what does headphone impedance mean", ["Headphones"]),
    ("hi", H, "ईयरबड्स को रीसेट कैसे करें", [f"{KB}headphones:procedure:reset_earbuds", f"{KB}headphones:cause:pairing_glitch"]),
    ("en", H, "why do lithium batteries swell", ["Lithium-ion battery", "Thermal runaway"]),
    ("en", T, "white powder on the remote battery springs", ["Battery leakage", "Alkaline battery", f"{KB}battery_toy:procedure:clean_corrosion", f"{KB}battery_toy:cause:contacts_corroded"]),
    ("en", T, "how to clean battery corrosion", [f"{KB}battery_toy:procedure:clean_corrosion", "Battery leakage", "Alkaline battery"]),
    ("en", T, "check if the tv remote works using a phone camera", [f"{KB}battery_toy:procedure:test_remote_ir", "Consumer IR", "Remote control"]),
    ("en", T, "how does an infrared remote control work", ["Consumer IR", "Remote control", "दूरस्थ नियंत्रण"]),
    ("en", T, "button battery swallowed by a child", ["Button cell"]),
    ("hinglish", T, "khilona chal nahi raha nayi battery bhi dali", [f"{KB}battery_toy:"]),
    ("en", T, "alkaline battery leaking potassium hydroxide", ["Alkaline battery", "Battery leakage"]),
    ("hi", T, "रिमोट काम नहीं कर रहा", [f"{KB}battery_toy:", "दूरस्थ नियंत्रण", "Remote control"]),
    ("en", G, "what to do if someone gets an electric shock", ["Electrical injury", "विद्युत स्पर्शाघात"]),
    ("en", G, "smell of gas in the kitchen what to do", ["Gas leak", "Liquefied petroleum gas", "द्रवित पेट्रोलियम गैस"]),
    ("en", G, "is LPG heavier than air", ["Liquefied petroleum gas", "द्रवित पेट्रोलियम गैस"]),
    ("en", G, "how to check continuity with a multimeter", ["Multimeter"]),
    ("en", G, "what temperature does solder melt at", ["Soldering"]),
    ("en", G, "thermal runaway in batteries", ["Thermal runaway", "Lithium-ion battery"]),
    ("hi", G, "बिजली का झटका लगने पर क्या करें", ["विद्युत स्पर्शाघात", "Electrical injury"]),
    ("en", G, "why are house wires different colours", ["Electrical wiring"]),
]


def relevant(passage, prefixes) -> bool:
    return any(passage.id.startswith(p) or passage.title.startswith(p) for p in prefixes)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="local", choices=["local", "supabase"])
    ap.add_argument("--no-filter", action="store_true", help="search all products (no product filter)")
    args = ap.parse_args()
    settings = Settings(_env_file=ROOT / "apps" / "api" / ".env")
    embedder = Embedder(settings.gemini_api_key)
    if args.backend == "local":
        backend = LocalBackend(ROOT / "ingest" / "corpus.jsonl", ROOT / "ingest" / "raw" / "embeddings.json")
    else:
        backend = SupabaseBackend(settings.supabase_url, settings.supabase_key)
    retriever = Retriever(backend, embedder)

    results = {}
    for mode in ("keyword", "vector", "hybrid"):
        r1 = r5 = mrr = 0.0
        misses = []
        for lang, product, q, rel in QUERIES:
            if mode != "keyword":
                time.sleep(0.05)
            hits = retriever.search(q, product=None if args.no_filter else product, k=10, mode=mode)
            ranks = [i for i, p in enumerate(hits, 1) if relevant(p, rel)]
            first = ranks[0] if ranks else None
            r1 += first == 1
            r5 += bool(first and first <= 5)
            mrr += 1 / first if first else 0
            if not first or first > 5:
                misses.append(q)
        n = len(QUERIES)
        results[mode] = {"recall@1": round(r1 / n, 3), "recall@5": round(r5 / n, 3), "mrr@10": round(mrr / n, 3), "misses@5": misses}
        print(mode, {k: v for k, v in results[mode].items() if k != "misses@5"})
    suffix = "-nofilter" if args.no_filter else ""
    out = ROOT / "eval" / "reports" / f"retrieval-v1-{args.backend}{suffix}.json"
    out.write_text(json.dumps({"backend": args.backend, "product_filter": not args.no_filter, "n": len(QUERIES), "results": results}, indent=1, ensure_ascii=False), encoding="utf-8")
    for q in results["hybrid"]["misses@5"]:
        print("  hybrid miss:", q)


if __name__ == "__main__":
    main()
