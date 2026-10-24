# Knowledge graph

Curated, cited repair knowledge per product: `causes → questions (likelihoods) → procedures (steps, cautions, sources)`.

The files live in [`apps/api/src/fixwithme_api/knowledge/`](../apps/api/src/fixwithme_api/knowledge/), so they ship inside the API's Docker image (the Render build context is `apps/api`). Each file is validated when the API starts:

- cause priors must sum to 1;
- each question has a likelihood for every cause, strictly between 0 and 1;
- every source referenced must be defined;
- safety level 3 ("professional only") procedures must not contain DIY steps.

Every DIY step at safety level 2 or above must cite a source; a test enforces this.

`review_status: draft` means the content comes from cited sources but no technician has reviewed it yet. The app shows it as **Curated**, not **Verified**.

| Product | File | Status |
|---|---|---|
| Ceiling fan | `ceiling_fan.yaml` | draft (R1) |

The likelihoods are hand-set starting beliefs. They will be calibrated against FixBench-IN (R2) and real outcomes (R9).
