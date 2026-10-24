# Fix with Me

An AI repair assistant for Indian households. It diagnoses faults in everyday items (fans, extension boards, headphones, toys, appliances, plumbing), guides you through safe repairs, finds the right parts, and tells you plainly when to call a professional.

The full plan is in [docs/blueprint.md](docs/blueprint.md). Platform limits we have verified are in [docs/constraints.md](docs/constraints.md).

## Repository layout

| Path | What lives there |
|---|---|
| `apps/web` | Next.js PWA (static export, deployed to Cloudflare Pages) |
| `apps/api` | FastAPI backend (deployed to Render) |
| `kb/` | Curated component knowledge graph (YAML) |
| `ingest/` | Manual and document ingestion for retrieval |
| `ml/` | Model training: classifiers, safety model, fine-tuning research |
| `eval/` | FixBench-IN benchmark and evaluation harness |
| `osm/` | OpenStreetMap India import for nearby shops |

## Local development

**API** (Python 3.12+):

```sh
cd apps/api
py -3.13 -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
cp .env.example .env   # add your Gemini key, or use the local Ollama provider
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
