"""Embeds every corpus chunk with gemini-embedding-001 (768 dims, L2-normalised).

Batches of 100 texts per request (the model is text-only, so lists are true batches).
Run: apps/api/.venv/Scripts/python ingest/embed.py   ->  ingest/raw/embeddings.json
"""

import json
import math
import sys
import time
from pathlib import Path

from google import genai
from google.genai import types

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api" / "src"))
from fixwithme_api.config import Settings  # noqa: E402

MODEL = "gemini-embedding-001"
DIMS = 768
BATCH = 100
CORPUS = ROOT / "ingest" / "corpus.jsonl"
OUT = ROOT / "ingest" / "raw" / "embeddings.json"


def doc_text(row: dict) -> str:
    return f"{row['title']}\n{row['text']}"


def normalise(v: list[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [round(x / n, 6) for x in v]


def main() -> None:
    key = Settings(_env_file=ROOT / "apps" / "api" / ".env").gemini_api_key
    client = genai.Client(api_key=key)
    rows = [json.loads(line) for line in CORPUS.read_text(encoding="utf-8").splitlines() if line.strip()]
    done = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    todo = [r for r in rows if r["id"] not in done]
    for i in range(0, len(todo), BATCH):
        batch = todo[i : i + BATCH]
        for attempt in range(4):
            try:
                res = client.models.embed_content(
                    model=MODEL,
                    contents=[doc_text(r) for r in batch],
                    config=types.EmbedContentConfig(output_dimensionality=DIMS, task_type="RETRIEVAL_DOCUMENT"),
                )
                break
            except Exception as exc:
                if attempt == 3:
                    raise
                print(f"  retry after error: {exc}", flush=True)
                time.sleep(10 * (attempt + 1))
        for r, e in zip(batch, res.embeddings, strict=True):
            done[r["id"]] = normalise(e.values)
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(done), encoding="utf-8")
        print(f"embedded {len(done)}/{len(rows)}", flush=True)
        time.sleep(4.2)
    stale = set(done) - {r["id"] for r in rows}
    for k in stale:
        del done[k]
    OUT.write_text(json.dumps(done), encoding="utf-8")
    print("done:", len(done), "vectors of", DIMS, "dims")


if __name__ == "__main__":
    main()
