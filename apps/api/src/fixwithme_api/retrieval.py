"""Hybrid retrieval over the corpus (curated KB + Wikipedia).

Candidates come from vector search (Gemini embeddings) and keyword search; the two rankings
are combined with reciprocal rank fusion (RRF). Two interchangeable backends:

- SupabaseBackend: pgvector + PGroonga via the `search_chunks` RPC (production).
- LocalBackend: the same algorithm in memory from ingest/corpus.jsonl + embeddings (tests,
  offline evaluation, and a fallback when the database is unreachable).
"""

import json
import logging
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Literal, Protocol

import httpx

log = logging.getLogger(__name__)

EMBED_MODEL = "gemini-embedding-001"
DIMS = 768
RRF_K = 60
POOL = 30
Mode = Literal["hybrid", "vector", "keyword"]
_WORD = re.compile(r"[\wऀ-ॿ]+")  # Devanagari vowel signs are not \w on their own

# Filler words dropped from keyword queries. PGroonga's default score counts matches without
# IDF, so with OR-joined terms these would rank long passages above relevant ones.
_STOPWORDS = frozenset(
    """a an the is are was were be been am do does did to of in on at for with from by and or
    but not no it its this that these those i my me we our you your he she they them what which
    who whom how why when where can could should would will shall may might must if then than
    so as there here up down out about into over after before again just very also any some
    instead using use get got has have had
    hai hain tha thi the ka ki ke ko se me mein par pe aur ya bhi kya kaise kyu kyon nahi na
    raha rahi rahe ho gaya gayi kar karna karta karti ek
    है हैं था थी थे का की के को से में पर और या भी क्या कैसे क्यों नहीं ना रहा रही रहे हो गया गई कर करें एक""".split()
)


def query_terms(query: str) -> list[str]:
    terms = _WORD.findall(query.lower())
    kept = [t for t in terms if t not in _STOPWORDS]
    return kept or terms  # an all-stopword query still searches something


@dataclass
class Passage:
    id: str
    title: str
    url: str | None
    license: str
    source_type: str
    lang: str
    product: str | None
    safety_level: int | None
    content: str
    vec_rank: int | None = None
    kw_rank: int | None = None
    score: float = 0.0


class Backend(Protocol):
    def candidates(
        self, query: str, vector: list[float] | None, product: str | None
    ) -> list[Passage]: ...


def fuse(cands: list[Passage], mode: Mode = "hybrid", k: int = 5) -> list[Passage]:
    out = []
    for p in cands:
        v = 1 / (RRF_K + p.vec_rank) if p.vec_rank and mode in ("hybrid", "vector") else 0.0
        w = 1 / (RRF_K + p.kw_rank) if p.kw_rank and mode in ("hybrid", "keyword") else 0.0
        if v or w:
            p.score = v + w
            out.append(p)
    return sorted(out, key=lambda p: p.score, reverse=True)[:k]


# ---------------------------------------------------------------- embeddings


class Embedder:
    def __init__(self, api_key: str | None) -> None:
        self._client = None
        if api_key:
            from google import genai

            self._client = genai.Client(api_key=api_key)

    @property
    def enabled(self) -> bool:
        return self._client is not None

    @lru_cache(maxsize=512)  # noqa: B019 - one Embedder per app; caching repeated questions saves quota
    def embed(self, text: str) -> tuple[float, ...] | None:
        if self._client is None:
            return None
        from google.genai import types

        try:
            res = self._client.models.embed_content(
                model=EMBED_MODEL,
                contents=[text],
                config=types.EmbedContentConfig(
                    output_dimensionality=DIMS, task_type="RETRIEVAL_QUERY"
                ),
            )
        except Exception as exc:  # quota or network: fall back to keyword search
            log.warning("query embedding failed: %s", exc)
            return None
        v = res.embeddings[0].values
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        return tuple(x / n for x in v)


# ---------------------------------------------------------------- backends


class SupabaseBackend:
    def __init__(self, url: str, key: str) -> None:
        self._client = httpx.Client(
            base_url=f"{url}/rest/v1",
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
            timeout=10.0,
        )

    def candidates(
        self, query: str, vector: list[float] | None, product: str | None
    ) -> list[Passage]:
        body = {
            "query_text": " ".join(query_terms(query)),
            "query_embedding": list(vector) if vector else [0.0] * DIMS,
            "product_filter": product,
            "pool": POOL,
        }
        resp = self._client.post("/rpc/search_chunks", json=body)
        resp.raise_for_status()
        rows = resp.json()
        if not vector:  # without a real query vector the vector ranks are meaningless
            for r in rows:
                r["vec_rank"] = None
        return [Passage(**r) for r in rows]


class LocalBackend:
    """In-memory BM25 + cosine over the corpus files; mirrors the database search."""

    def __init__(self, corpus: Path, embeddings: Path | None) -> None:
        rows = [
            json.loads(line)
            for line in corpus.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        vecs = (
            json.loads(embeddings.read_text(encoding="utf-8"))
            if embeddings and embeddings.exists()
            else {}
        )
        self.passages = [
            Passage(
                id=r["id"],
                title=r["title"],
                url=r.get("url"),
                license=r["license"],
                source_type=r["source_type"],
                lang=r["lang"],
                product=r.get("product"),
                safety_level=r.get("safety_level"),
                content=r["text"],
            )
            for r in rows
        ]
        self.vectors = [vecs.get(p.id) for p in self.passages]
        self.tokens = [
            Counter(_WORD.findall((p.title + " " + p.content).lower())) for p in self.passages
        ]
        self.lengths = [sum(t.values()) for t in self.tokens]
        self.avg_len = sum(self.lengths) / max(len(self.lengths), 1)
        df = Counter(term for t in self.tokens for term in t)
        n = len(self.passages)
        self.idf = {term: math.log(1 + (n - d + 0.5) / (d + 0.5)) for term, d in df.items()}

    def _bm25(self, i: int, terms: list[str], k1: float = 1.4, b: float = 0.75) -> float:
        tf, dl = self.tokens[i], self.lengths[i]
        score = 0.0
        for t in terms:
            if t in tf:
                f = tf[t]
                score += self.idf[t] * f * (k1 + 1) / (f + k1 * (1 - b + b * dl / self.avg_len))
        return score

    def candidates(
        self, query: str, vector: list[float] | None, product: str | None
    ) -> list[Passage]:
        idx = [
            i
            for i, p in enumerate(self.passages)
            if product is None or p.product == product or p.product is None
        ]
        terms = query_terms(query)
        kw = sorted(((self._bm25(i, terms), i) for i in idx), reverse=True)
        kw_rank = {i: r for r, (s, i) in enumerate(kw[:POOL], 1) if s > 0}
        vec_rank = {}
        if vector:
            sims = sorted(
                (
                    (sum(a * b for a, b in zip(vector, self.vectors[i], strict=True)), i)
                    for i in idx
                    if self.vectors[i]
                ),
                reverse=True,
            )
            vec_rank = {i: r for r, (_, i) in enumerate(sims[:POOL], 1)}
        out = []
        for i in set(kw_rank) | set(vec_rank):
            p = self.passages[i]
            out.append(
                Passage(**{**p.__dict__, "vec_rank": vec_rank.get(i), "kw_rank": kw_rank.get(i)})
            )
        return out


@dataclass
class Retriever:
    backend: Backend | None
    embedder: Embedder
    fallback: Backend | None = None
    last_error: str | None = field(default=None, init=False)

    @property
    def enabled(self) -> bool:
        return self.backend is not None

    def search(
        self, query: str, product: str | None = None, k: int = 5, mode: Mode = "hybrid"
    ) -> list[Passage]:
        if self.backend is None:
            return []
        vector = self.embedder.embed(query) if mode != "keyword" else None
        try:
            cands = self.backend.candidates(query, list(vector) if vector else None, product)
        except Exception as exc:
            log.warning("retrieval backend failed: %s", exc)
            self.last_error = str(exc)
            if self.fallback is None:
                return []
            cands = self.fallback.candidates(query, list(vector) if vector else None, product)
        return fuse(cands, mode, k)


def build_retriever(settings) -> Retriever:
    """Supabase in production; the local backend (if its files are configured) as a fallback."""
    embedder = Embedder(settings.gemini_api_key)
    local = None
    if settings.retrieval_corpus:
        emb = Path(settings.retrieval_embeddings) if settings.retrieval_embeddings else None
        local = LocalBackend(Path(settings.retrieval_corpus), emb)
    if settings.retrieval == "off":
        return Retriever(None, embedder)
    if settings.retrieval == "local":
        return Retriever(local, embedder)
    if settings.supabase_url and settings.supabase_key:
        return Retriever(
            SupabaseBackend(settings.supabase_url, settings.supabase_key), embedder, local
        )
    return Retriever(local, embedder)
