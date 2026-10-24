# Fix with Me

An AI repair assistant for Indian households, in English and Hindi. Tell Fixy what's broken by typing, talking or taking a photo. It asks a few questions, names the likely fault, and walks you through a safe fix. It also tells you plainly when to stop and call a professional.

**Live:** https://fixwithme.avirajvirape601.workers.dev

## What it does

- **Diagnosis** for ceiling fans, extension boards, headphones/earbuds and toys/remotes. A Bayesian engine over a curated knowledge base picks the most informative question to ask next. It works even when the AI quota runs out.
- **Safety first.** Rules in English, Hinglish and Hindi, plus a small trained classifier, stop the chat with clear actions and a 112 call button for burning, smoke, shock, gas, water near power, swollen batteries or swallowed button cells.
- **Step-by-step guides** with tools, time, a ₹ estimate and cited sources, plus "Buy the part" links that search Amazon or Flipkart for the exact spec. No affiliate links.
- **Follow-up questions** are answered only from cited sources (curated guides and Wikipedia, hybrid search in Supabase). A second model checks each point, and Fixy says "not sure" when the sources don't cover it.
- **Any other item:** a web-search-grounded suggestion, limited to safe outside checks and labelled "AI suggestion · unverified", plus a "Find a repair shop" link.
- **Photo and voice:** the photo is shrunk and location data removed on the phone, then Gemini names the item. Voice uses the browser's speech recognition.

## Results (measured, see `eval/reports/`)

| Benchmark | Result |
|---|---|
| FixBench-IN v1 diagnosis (94 cases) | top-1 90.7%, top-3 96.0%, STOP recall 100%, false STOPs 0%; plain Gemini: top-1 81.3%, STOP recall 84.6% |
| QA v1 (70 questions) | answerable correct 92.5% (plain Gemini 87.5%); claims outside sources 0% (34%); "not sure" when uncovered 12/12 (1/12); unsafe answers 0 (1) |
| Retrieval (42 queries, Supabase) | hybrid recall@5 100%, recall@1 90.5% |
| Safety classifier FT-1 (128 held-out) | hazard recall: rules 67.2% → rules + FT-1 89.1% |

These are small sets written by the project author. Treat the numbers as indicative.

The design is in [docs/design.md](docs/design.md), and the verified platform limits are in [docs/constraints.md](docs/constraints.md). The original long-range plan is in [docs/blueprint.md](docs/blueprint.md); a leaner scope shipped (no accounts, live prices or model fine-tuning).

## Repository layout

| Path | What lives there |
|---|---|
| `apps/web` | Next.js static app (Cloudflare Workers static assets) |
| `apps/api` | FastAPI backend (Render), knowledge base YAML in `src/fixwithme_api/knowledge/` |
| `ingest/` | Corpus build (Wikipedia + KB), embeddings, Supabase loader |
| `supabase/` | Database migrations |
| `ml/` | Safety classifier (FT-1) training and model card |
| `eval/` | FixBench-IN diagnosis and QA benchmarks, retrieval eval, reports |

## Local development

**API** (Python 3.12+):

```sh
cd apps/api
py -3.13 -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
cp .env.example .env   # add your Gemini key (and Supabase, or set FWM_RETRIEVAL=off)
.venv/Scripts/python -m uvicorn fixwithme_api.main:app --reload
.venv/Scripts/python -m pytest
```

**Web** (Node 22, pnpm):

```sh
cd apps/web
pnpm install
pnpm dev     # http://localhost:3000, expects the API on http://localhost:8000
pnpm build   # static export to apps/web/out
```

Set `NEXT_PUBLIC_API_URL` to point the web app at a deployed API.

## Deployments

| Part | Where | URL |
|---|---|---|
| API | Render (free, Singapore), auto-deploys from `main` | https://fixwithme-api.onrender.com |
| Web | Cloudflare Workers (static assets), auto-deploys from `main` | https://fixwithme.avirajvirape601.workers.dev |
| Database | Supabase project `fixwithme` (free, Mumbai `ap-south-1`) | https://hphjixlvvpdvvadyhsrc.supabase.co |

The API sleeps after 15 minutes idle and takes about a minute to wake up.
