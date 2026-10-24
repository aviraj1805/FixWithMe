"""Builds the retrieval corpus: our curated knowledge base + selected Wikipedia articles.

Licensing: Wikipedia text is CC BY-SA 4.0. Every chunk keeps its article URL and licence, and
the app shows the source with each excerpt. Brand manuals are not included yet (copyright).

Run with the API virtualenv from the repo root:
  apps/api/.venv/Scripts/python ingest/build_corpus.py      ->  ingest/corpus.jsonl
"""

import hashlib
import json
import re
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api" / "src"))
from fixwithme_api import knowledge  # noqa: E402

RAW = ROOT / "ingest" / "raw"
OUT = ROOT / "ingest" / "corpus.jsonl"
UA = {"User-Agent": "FixWithMe/0.4 (https://github.com/aviraj1805/FixWithMe)"}
WIKI_LICENSE = "CC BY-SA 4.0"

# (language, title, product it informs or None for general safety)
ARTICLES = [
    ("en", "Ceiling fan", "ceiling_fan"),
    ("en", "Motor capacitor", "ceiling_fan"),
    ("en", "Capacitor", "ceiling_fan"),
    ("en", "Induction motor", "ceiling_fan"),
    ("en", "Power strip", "extension_board"),
    ("en", "Extension cord", "extension_board"),
    ("en", "Circuit breaker", "extension_board"),
    ("en", "Residual-current device", "extension_board"),
    ("en", "Fuse (electrical)", "extension_board"),
    ("en", "AC power plugs and sockets", "extension_board"),
    ("en", "Headphones", "headphones"),
    ("en", "Phone connector (audio)", "headphones"),
    ("en", "Bluetooth", "headphones"),
    ("en", "Lithium-ion battery", "headphones"),
    ("en", "Alkaline battery", "battery_toy"),
    ("en", "Battery leakage", "battery_toy"),
    ("en", "Button cell", "battery_toy"),
    ("en", "Remote control", "battery_toy"),
    ("en", "Consumer IR", "battery_toy"),
    ("en", "Electrical injury", None),
    ("en", "Gas leak", None),
    ("en", "Liquefied petroleum gas", None),
    ("en", "Thermal runaway", None),
    ("en", "Electrical wiring", None),
    ("en", "Soldering", None),
    ("en", "Multimeter", None),
    ("hi", "पंखा", "ceiling_fan"),
    ("hi", "संधारित्र", "ceiling_fan"),
    ("hi", "हेडफ़ोन", "headphones"),
    ("hi", "ब्लूटूथ", "headphones"),
    ("hi", "रिमोट कंट्रोल", "battery_toy"),
    ("hi", "परिपथ वियोजक", "extension_board"),
    ("hi", "बैटरी", "battery_toy"),
    ("hi", "विद्युत आघात", None),
    ("hi", "द्रवित पेट्रोलियम गैस", None),
]

SKIP_SECTIONS = re.compile(
    r"^(references|external links|see also|further reading|notes|bibliography|gallery|sources|"
    r"citations|history|etymology|in popular culture|patents|manufacturers|market|"
    r"सन्दर्भ|संदर्भ|बाहरी कड़ियाँ|इन्हें भी देखें|इतिहास)\b",
    re.IGNORECASE,
)
# The plugs article is a world survey; only India-relevant parts help users here.
KEEP_ONLY = {"AC power plugs and sockets": re.compile(r"india|type d|type m|safety|earth", re.IGNORECASE)}
MAX_WORDS, MIN_WORDS = 170, 25
MAX_CHUNKS_PER_ARTICLE = 16  # the lead and main sections; later sections drift off-topic


def fetch(lang: str, title: str) -> dict | None:
    cache = RAW / f"wiki-{lang}-{hashlib.sha1(title.encode()).hexdigest()[:12]}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    params = {
        "action": "query", "prop": "extracts|info|revisions", "explaintext": 1, "titles": title,
        "format": "json", "redirects": 1, "inprop": "url", "rvprop": "ids",
    }
    for attempt in range(4):  # the connection here drops now and then
        try:
            r = httpx.get(f"https://{lang}.wikipedia.org/w/api.php", params=params, headers=UA, timeout=30)
            r.raise_for_status()
            break
        except httpx.HTTPError:
            if attempt == 3:
                raise
            time.sleep(2 * (attempt + 1))
    page = next(iter(r.json()["query"]["pages"].values()))
    if "missing" in page or not page.get("extract"):
        return None
    data = {
        "lang": lang, "title": page["title"], "url": page["fullurl"],
        "revision": page["revisions"][0]["revid"], "text": page["extract"],
    }
    RAW.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    time.sleep(0.5)  # be gentle with the API
    return data


def sections(text: str) -> list[tuple[str, str]]:
    """Split a plain-text extract on '== Heading ==' lines into (heading path, body)."""
    out, path, buf = [], [], []
    for line in text.splitlines():
        m = re.match(r"^(=+)\s*(.*?)\s*=+$", line.strip())
        if m:
            if buf:
                out.append((" › ".join(path), "\n".join(buf).strip()))
            level = len(m.group(1)) - 1
            path = path[: max(level - 1, 0)] + [m.group(2)]
            buf = []
        else:
            buf.append(line)
    if buf:
        out.append((" › ".join(path), "\n".join(buf).strip()))
    return out


def chunk(body: str) -> list[str]:
    paras = [p.strip() for p in re.split(r"\n\s*\n|\n", body) if p.strip()]
    chunks, cur = [], []
    for p in paras:
        words = p.split()
        if cur and len(cur) + len(words) > MAX_WORDS:
            chunks.append(" ".join(cur))
            cur = []
        while len(words) > MAX_WORDS:  # very long paragraph: split on sentences
            head, words = words[:MAX_WORDS], words[MAX_WORDS:]
            chunks.append(" ".join(head))
        cur += words
    if cur:
        chunks.append(" ".join(cur))
    return [c for c in chunks if len(c.split()) >= MIN_WORDS]


def wiki_chunks() -> list[dict]:
    rows = []
    for lang, title, product in ARTICLES:
        page = fetch(lang, title)
        if page is None:
            print(f"  skipped (missing): {lang}:{title}")
            continue
        keep = KEEP_ONLY.get(page["title"])
        n = 0
        for heading, body in sections(page["text"]):
            top = heading.split(" › ")[0] if heading else ""
            if top and SKIP_SECTIONS.match(top):
                continue
            if keep and not keep.search(heading + " " + body[:300]):
                continue
            for text in chunk(body):
                if n >= MAX_CHUNKS_PER_ARTICLE:
                    break
                rows.append({
                    "id": f"wiki:{lang}:{page['revision']}:{n}",
                    "source_type": "wikipedia",
                    "title": page["title"] + (f" — {heading}" if heading else ""),
                    "url": page["url"],
                    "license": WIKI_LICENSE,
                    "lang": lang,
                    "product": product,
                    "text": text,
                })
                n += 1
        print(f"  {lang}:{page['title']}: {n} chunks")
    return rows


def kb_chunks() -> list[dict]:
    """Our curated knowledge as passages: one per cause and one per procedure, EN and HI."""
    rows = []
    for pid in knowledge.available():
        kb = knowledge.load(pid)
        for lang in ("en", "hi"):
            for c in kb.causes:
                proc = kb.procedures[c.procedure]
                text = f"{kb.names.get(lang)}: {c.name.get(lang)}. " + (
                    f"Fix: {proc.title.get(lang)}." if lang == "en" else f"समाधान: {proc.title.get(lang)}।"
                )
                if proc.part_spec and lang == "en":
                    text += f" Replacement part: {proc.part_spec.kind}. {proc.part_spec.match}"
                src = kb.sources[c.sources[0]] if c.sources else None
                rows.append({
                    "id": f"kb:{pid}:cause:{c.id}:{lang}", "source_type": "kb",
                    "title": f"{kb.names.get(lang)} — {c.name.get(lang)}",
                    "url": src.url if src else None, "license": "Fix with Me curated", "lang": lang,
                    "product": pid, "text": text,
                })
            for proc_id, proc in kb.procedures.items():
                parts = [f"{kb.names.get(lang)}: {proc.title.get(lang)}."]
                if proc.safety_level >= 3:
                    parts.append(f"{proc.reason.get(lang)} {proc.professional.get(lang)}.")
                for i, s in enumerate(proc.steps, 1):
                    parts.append(f"{i}. {s.text.get(lang)}" + (f" ({s.caution.get(lang)})" if s.caution else ""))
                if proc.verify:
                    parts.append(proc.verify.get(lang))
                if proc.prevent:
                    parts.append(proc.prevent.get(lang))
                srcs = sorted(proc.source_ids())
                rows.append({
                    "id": f"kb:{pid}:procedure:{proc_id}:{lang}", "source_type": "kb",
                    "title": f"{kb.names.get(lang)} — {proc.title.get(lang)}",
                    "url": kb.sources[srcs[0]].url if srcs else None,
                    "license": "Fix with Me curated", "lang": lang, "product": pid,
                    "safety_level": proc.safety_level, "text": " ".join(parts),
                })
    return rows


def main() -> None:
    rows = kb_chunks() + wiki_chunks()
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids)), "duplicate chunk ids"
    with OUT.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    from collections import Counter

    words = sum(len(r["text"].split()) for r in rows)
    print(len(rows), "chunks,", words, "words")
    print("by source:", dict(Counter(r["source_type"] for r in rows)))
    print("by lang:", dict(Counter(r["lang"] for r in rows)))
    print("by product:", dict(Counter(r["product"] or "general" for r in rows)))


if __name__ == "__main__":
    main()
