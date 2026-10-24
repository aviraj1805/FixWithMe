"""Load ingest/corpus.jsonl + embeddings into Supabase (public.chunks) and prune stale rows.

Writes go through the token-checked `ingest_chunks` / `prune_chunks` RPCs, so only the
publishable key is needed; the ingest token lives in apps/api/.env (FWM_INGEST_TOKEN) and
only its SHA-256 hash is stored in the database.

Usage (repo root, API venv):
  apps/api/.venv/Scripts/python ingest/load.py
"""

import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api" / "src"))
from fixwithme_api.config import Settings  # noqa: E402

BATCH = 50


def main() -> None:
    env = ROOT / "apps" / "api" / ".env"
    settings = Settings(_env_file=env)
    token = next(
        (ln.split("=", 1)[1].strip() for ln in env.read_text(encoding="utf-8").splitlines()
         if ln.startswith("FWM_INGEST_TOKEN=")),
        None,
    )
    if not (settings.supabase_url and settings.supabase_key and token):
        sys.exit("Need FWM_SUPABASE_URL, FWM_SUPABASE_KEY and FWM_INGEST_TOKEN in apps/api/.env")

    rows = [json.loads(ln) for ln in (ROOT / "ingest" / "corpus.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip()]
    vectors = json.loads((ROOT / "ingest" / "raw" / "embeddings.json").read_text(encoding="utf-8"))
    missing = [r["id"] for r in rows if r["id"] not in vectors]
    if missing:
        sys.exit(f"{len(missing)} chunks have no embedding (run ingest/embed.py): {missing[:3]}")

    client = httpx.Client(
        base_url=f"{settings.supabase_url}/rest/v1",
        headers={"apikey": settings.supabase_key, "Authorization": f"Bearer {settings.supabase_key}"},
        timeout=60.0,
    )
    loaded = 0
    for i in range(0, len(rows), BATCH):
        batch = [
            {**r, "embedding": "[" + ",".join(f"{x:.7f}" for x in vectors[r["id"]]) + "]"}
            for r in rows[i : i + BATCH]
        ]
        resp = client.post("/rpc/ingest_chunks", json={"token": token, "rows": batch})
        if resp.status_code != 200:
            sys.exit(f"ingest failed at batch {i // BATCH}: {resp.status_code} {resp.text[:300]}")
        loaded += resp.json()
        print(f"loaded {loaded}/{len(rows)}")
    resp = client.post("/rpc/prune_chunks", json={"token": token, "keep_ids": [r["id"] for r in rows]})
    resp.raise_for_status()
    print(f"pruned {resp.json()} stale rows")


if __name__ == "__main__":
    main()
