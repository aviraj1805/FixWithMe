# Fix with Me: Full-Product Blueprint

## Context
Fix with Me is an AI repair assistant for Indian households. It covers **any household item or electronic device**: fan capacitors, extension boards, headphones, speakers, kids' toys, appliances, plumbing, RO purifiers. It guides users from diagnosis to repair to buying parts.

**The USP is the reliability and accuracy of its answers, proven on a public benchmark.**

It is planned as a **full product, not an MVP**. Every feature below is in scope and ships through staged releases. Each release is deployed and usable, which avoids rework. The repo `E:\FixWithMe` is empty. Approving this plan starts Release R0.

### Locked decisions
| Topic | Decision |
|---|---|
| Users / region | Indian households, adults 18+. EN + HI. INR, 230V |
| Coverage | All items, through a component-level knowledge graph. Tiers: A Verified, B Component-verified, C AI suggestion |
| USP | Measured reliability: verified generation pipeline + FixBench-IN benchmark |
| LLM | Gemini free tier with privacy mitigations. Local Gemma 4 for dev, eval and fallback. `LLMProvider` abstraction |
| Live mode | Hybrid on-device CV/OCR + tap-to-send frames + push-to-talk. Gemini Live streaming in a later release |
| Training | FT-1 safety classifier, FT-2 claim verifier, FT-3 Gemma 4 QLoRA research, appliance image classifier, Bayesian engine |
| Commerce | **Live prices, stock, cart and checkout handoff** through affiliate programs (Amazon.in, Flipkart). User pays on the retailer. No business registration, so no ONDC and no payment handling |
| Budget | Free quotas only. Prices carry a "last checked" timestamp |
| Stack | Next.js (static PWA) + FastAPI + Supabase |
| Status change | The project becomes **commercial** (affiliate income as an individual with a PAN). This affects hosting, terms and disclosures (see §2 and §8) |

### Research findings that shaped the plan
- **Gemini:** fine-tuning is not available in the Gemini API (ended May 2025). The free tier says "Do not submit sensitive, confidential, or personal information". Inputs may be human-reviewed. Users must be 18+. A $5 prepaid paid tier with a hard stop exists as an upgrade path. Per-model free limits are visible only in AI Studio (check at R0).
- **Local LLM:** your RTX 2050 (4 GB) and 16 GB RAM run Gemma 4 E2B/E4B quantized, which is fine for dev and eval. No free GPU host exists, so it can't serve the public.
- **Pre-training:** infeasible. Facts come from curated knowledge plus retrieval. Fine-tuning goes to classifiers and verifiers, where it actually helps.
- **iFixit:** CC BY-NC-SA; the terms forbid AI training and the site is for personal use. Commercial use is now ruled out, so **link out only**, with attribution.
- **Amazon:** PA-API is retired (Apr–May 2026). Creators API access needs Associates membership and **10 qualifying sales in 30 days** (per the .com docs; check for .in) and is revoked if sales stop. Displayed prices must come from the API, with a timestamp if refreshed less often than hourly.
- **Flipkart Affiliate API:** product feed, search, price and stock exist, but the docs date from 2016 and are marked "beta". Live status will be confirmed at signup (R6 gate).
- **SerpApi Google Shopping:** a legitimate live multi-seller price API. The free tier is about 100 searches a month.
- **Vercel Hobby:** non-commercial only. Affiliate-driven sites count as commercial, so **the static frontend goes on Cloudflare Pages** (commercial terms confirmed at R0).
- **Render free:** sleeps after 15 min, ~1 min cold start, 750 h a month, ephemeral disk.
- **Supabase free:** 500 MB DB, pauses after 7 idle days.
- **OSM:** the public Nominatim and Overpass APIs aren't meant as an app backend, so do an offline Geofabrik import with ODbL attribution.
- **Open Images V7:** confirmed classes include Washing machine, Tap, Sink, Toilet, Refrigerator, Microwave oven, Gas stove, Pressure cooker, Kettle, Mixer, Ceiling/Mechanical fan, Television, Light bulb, Power plugs and sockets. Missing: RO purifier, water heater, AC.
- **Indian law:** CEA Safety Regulations 2023 require licensed contractors for electrical installation work, with an exemption for minor replacement of appliances up to 250V. The Consumer Protection (E-Commerce) Rules and ASCI disclosure norms apply to affiliate content. DPDP Act 2023 applies to personal data.

---

## The USP: a reliability stack
1. **Component knowledge graph:** `product_type → components → failure_modes → symptoms → tests → fixes → part_specs`. It holds ~50–70 shared components:
   - power: cord/plug, fuse/thermal fuse, switches, socket contacts, run capacitors, regulators, SMPS adapters;
   - batteries: alkaline, button cell, Li-ion;
   - contacts and wiring: battery contacts, solder joints, cables, 3.5 mm/USB jacks;
   - electronics: tact buttons, LEDs, speaker drivers, DC motors, PCB traces;
   - mechanical: bearings, belts;
   - appliance parts: heating elements, thermostats;
   - water: pumps, solenoid valves, hoses, O-rings, cartridges, flush valves, filters and membranes.

   Each node has citations, a safety level 0–3, a ₹ cost range and the specification of the replacement part.
2. **Coverage tiers on every answer:**
   - **A (Verified):** the family is curated.
   - **B (Component-verified):** the LLM maps the item to components, the user confirms, and the engine reasons over verified nodes.
   - **C (AI suggestion):** grounded web answer, capped at safety level 1, labelled "unverified".
3. **Verified generation:**
   - Hybrid retrieval, then a draft constrained to the evidence.
   - The draft is split into atomic claims, and the verifier checks each one (unsupported claims are dropped or flagged).
   - Self-consistency on the diagnosis, calibrated confidence and abstention.
   - The safety gate runs before and after.
4. **Bayesian diagnostic engine:** noisy-OR / naive Bayes over the knowledge graph. The next question is chosen by expected information gain, weighted by test cost and safety. Priors update from outcomes (Beta/Dirichlet). It runs without the LLM, so the core flow survives quota exhaustion.
5. **FixBench-IN:** a public benchmark of Indian repair scenarios and questions in EN/HI/Hinglish, including safety-critical cases.

   It compares: (a) vanilla Gemini; (b) + RAG; (c) + verifier and abstention; (d) + engine; (e) fine-tuned Gemma 4 ± RAG.

   Metrics: factual accuracy, unsupported-claim rate, safety-critical error rate, risk–coverage curve, ECE. It also scores part-spec matching precision for the commerce features.
6. **Fine-tuning:**
   - **FT-1** safety-risk classifier: a multilingual small encoder, chosen at R2. ONNX int8, runs in the browser and on the API.
   - **FT-2** claim verifier: an NLI cross-encoder trained on repair-domain pairs. Gemma or Gemini acts as judge until it's ready.
   - **FT-3** Gemma 4 E2B/E4B QLoRA on verified instructions distilled from the KB. The result is published either way, and it's deployed only if it wins and hosting allows.

## 1. Product scope (full v1.0)
**Diagnosis and repair:**
- Inputs: text, photos, live camera with on-device classification and OCR, voice (EN/HI).
- Product identification: classifier, rating-label OCR, brand model-number parser, user confirmation.
- Safety triage first. Adaptive questions. Ranked causes with evidence, confidence and tier labels.
- Step-by-step guides: tools, time, ₹ cost, difficulty, verification steps.
- Prevention tips and maintenance reminders.
- Follow-up chat that keeps session context.
- History, outcomes, analytics.

**Commerce:**
- Spec-based part finder.
- **Live prices and stock** from Flipkart and Amazon APIs, plus SerpApi multi-seller.
- Compatibility shown as "matches spec" or "unverified".
- Price comparison and price history (non-Amazon sources only, subject to their terms).
- **Multi-retailer cart, then checkout handoff** (Amazon cart-add link and Flipkart product links, with affiliate tags).
- Nearby repair shops and hardware stores (OSM). "Call to check stock": we have no local stock data, and we say so.
- Authorised service-centre links.

**Later releases, still in scope:**
- Gemini Live streaming mode.
- Visible-damage classifier trained on consented uploads.
- Maintenance reminders with push notifications.
- Own-store checkout only if a compliance review allows it for an individual (Razorpay no-GST route). Otherwise it stays out.

**Permanently out (product policy, not scope cuts)** — the app gives refer-to-professional only:
- gas and LPG appliances;
- fixed wiring (MCB, distribution board, wall sockets);
- geysers;
- refrigerant;
- microwave internals;
- opening SMPS chargers or adapters;
- swollen Li-ion batteries.

## 2. Technology stack
| Layer | Choice | Why |
|---|---|---|
| Frontend | Next.js (TypeScript, static export) + Tailwind v4 + shadcn/ui/Radix + Motion + Lucide + Recharts + MapLibre + next-intl + Storybook, PWA, on **Cloudflare Pages** (design system in §7b) | Your stack. Static hosting is free and permits commercial use. All dynamic logic lives in the API |
| On-device ML | ONNX Runtime Web (classifiers, FT-1), Tesseract.js eng+hin, MediaPipe face detector, Web Speech API, `speechSynthesis` | Free and private. Cuts LLM calls |
| API | FastAPI (Python 3.12), Pydantic v2, SQLAlchemy 2/asyncpg, APScheduler for price refresh, on **Render free** | One language for ML and the backend |
| Data | Supabase free: Postgres + pgvector + PostGIS + full-text + Auth (Google) + Storage, with RLS | One free service covers everything |
| AI | Gemini Flash-class model (configurable), falling back to Flash-Lite, then engine-only. 2.5 Flash for search grounding (500 free/day). `gemini-embedding-2` @768 | Free, multimodal, Hindi |
| Local | Ollama + Gemma 4 E4B (dev, eval, judge) | Saves quota. Model comparison |
| Training | PyTorch, timm, HF Transformers/PEFT, Colab/Kaggle, RTX 2050 | Free GPUs |
| Commerce | Flipkart Affiliate API, Amazon Creators API (once eligible), SerpApi (free quota), affiliate deep links | Legitimate sources only |
| Ops | GitHub Actions, Sentry free, JSON logs, `llm_calls` and `provider_calls` audit tables | Enough at this scale |

## 3. Architecture
```
PWA (Cloudflare Pages)
  camera → ONNX classifier → hint │ privacy filter (crop, face blur, EXIF strip) → frame on tap
  label  → Tesseract.js → model parser → confirm │ mic → Web Speech → text │ FT-1 safety pre-check
        │ HTTPS + Supabase JWT
FastAPI (Render)
  Safety Gate (rules + FT-1) ── before/after every LLM step
  Session Orchestrator: identify → triage → questions → diagnose → guide → verify → parts → outcome
  ├─ Extractor (Gemini JSON)        ├─ Bayesian Engine (KG)        ├─ Hybrid Retriever (pgvector+tsvector, RRF)
  ├─ Composer + Claim Verifier      ├─ PII Scrubber + Quota Manager ├─ Places (PostGIS)
  └─ Commerce: Part-Spec Resolver → Provider adapters (Flipkart | Amazon | SerpApi) → Listing-attribute
              extractor → Spec Matcher → Offer cache (TTL + timestamp) → Cart → Affiliate handoff URLs
Supabase (KG, sessions, chunks, offers, places, outcomes, audit) · Gemini · (dev) Ollama
Offline: kb/ (YAML→DB) · ingest/ (manuals→chunks) · osm/ (India PBF→POIs) · ml/ (training) · eval/ (FixBench-IN)
```

## 4. AI/ML components
| Component | Data | Method | Metrics |
|---|---|---|---|
| Bayesian engine | KG likelihoods and priors, outcomes | Noisy-OR, info-gain questions, Beta updates | Top-1/3, questions to p≥0.8, Brier/ECE vs baseline |
| Symptom extractor | ~300+ labelled EN/HI/Hinglish utterances | Gemini JSON schema (Gemma comparison) | Slot F1 |
| Component mapper (Tier B) | Product→component pairs from the KG | Gemini + KG constraint check | Mapping precision |
| Appliance classifier | Open Images crops + self-collected RO and small-electronics photos | MobileNetV3/EfficientNet-B0 → ONNX int8 | Macro-F1, per-class recall, MB, phone latency |
| Label OCR | ~50+ label photos | Tesseract.js → regex → Gemini on crop | Model-number exact match, CER |
| RAG | Manuals, KG text, Wikipedia (CC BY-SA), datasheets | Section chunks, hybrid RRF, metadata filters, abstention | Recall@5, MRR, citation support |
| FT-1 safety classifier | ~2–3k reviewed hazard utterances | Multilingual small encoder fine-tune | Recall per hazard class (gate: hard-block recall on test set) |
| FT-2 claim verifier | (evidence, claim, label) pairs from the KG | NLI cross-encoder fine-tune | Accuracy/F1 vs LLM judge |
| FT-3 Gemma 4 QLoRA | Verified instructions distilled from the KB | PEFT QLoRA | FixBench-IN vs RAG-Gemini |
| Listing-attribute extractor | Retailer titles and specs → (µF, V, wattage, connector, size) | Rules + Gemini JSON, later a small fine-tuned NER | Attribute precision/recall; false "match" rate |
| Analytics / DS | Outcomes, offers, funnel | SQL/pandas dashboards, price-trend stats, prior updating | Real data only |
| Damage classifier (later) | Consented uploads | Fine-tuned CNN | Macro-F1 |

## 5. Data and knowledge sources
| Source | Use | Constraint → decision |
|---|---|---|
| Your curated KG (`kb/` YAML) | Primary verified knowledge | Your own words with citations. A technician reviewer is recommended |
| Indian brand manuals (IFB, LG, Samsung, Whirlpool, Bosch, Crompton, Havells, Usha, Orient, boAt, Kent, Aquaguard, Pureit, Livpure) | RAG, error codes | Copyrighted. Index, show short excerpts with a source link, no PDF redistribution, respect robots.txt and terms. Grey area, not legal advice |
| Wikipedia, datasheets, BIS standards | Component facts and ratings | CC BY-SA or public. Attribute |
| iFixit | Guide links only | NC licence and anti-training terms, so link out with attribution |
| Open Images V7 | Classifier | CC BY 4.0 annotations. Attribution file |
| OSM via Geofabrik India | Shops and repair services | ODbL attribution. Patchy coverage, so also a "Search on Google Maps" link |
| Flipkart Affiliate API | Live price, stock, links | Status confirmed at the R6 gate. Follow affiliate terms |
| Amazon Creators API | Live price and stock | Unlocks after 10 sales in 30 days. Until then, links only and **no Amazon prices shown**. Timestamps required |
| SerpApi Google Shopping (gl=in) | Multi-seller prices | ~100 searches a month, so used only for a scheduled refresh of the top-N part specs, cached and timestamped |
| Gemini Search grounding | Tier-C answers | Show Google's search entry point and sources |

## 6. Database and API
**Knowledge graph:**
- `product_types`, `components`, `product_components`
- `failure_modes`, `symptoms`, `fm_symptom` (likelihoods), `tests`
- `procedures` (steps, tools, minutes, cost range, difficulty, safety_level, verification, prevention)
- `error_codes`, `part_specs` (attributes JSON), `safety_rules`, `sources`

**Retrieval:** `documents`, `chunks` (tsvector, `vector(768)`, metadata).

**Sessions:** `sessions`, `messages`, `observations` (origin, confidence), `product_ids`, `hypothesis_snapshots`, `outcomes`.

**Commerce:**
- `listings` (provider, external_id, title, url, attributes)
- `offers` (listing_id, price_inr, in_stock, fetched_at, provider)
- `spec_matches` (part_spec_id, listing_id, status: match/partial/unverified, evidence)
- `carts`, `cart_items`, `handoffs` (clicks)
- `price_history` (non-Amazon only, subject to terms)

**Ops:** `places`, `llm_calls`, `provider_calls`, `consents`, `reminders`. Row-level security on everything user-owned.

**API (REST + SSE):**
- **Sessions:**
  - `POST /sessions`
  - `POST /sessions/{id}/inputs`
  - `GET /sessions/{id}/next`
  - `POST /sessions/{id}/answers`
  - `GET /sessions/{id}/diagnosis`
  - `GET /procedures/{id}`
  - `POST /sessions/{id}/chat`
  - `POST /sessions/{id}/outcome`
- **Commerce:**
  - `GET /parts/{spec_id}/offers` (live, falling back to cache, always with `fetched_at`)
  - `POST /cart/items`
  - `GET /cart`
  - `POST /cart/checkout`, which returns per-retailer handoff URLs and logs the handoffs
- **Places and account:**
  - `GET /places/nearby`
  - `GET /me/history`
  - `DELETE /me/data`
  - `POST /reminders`
- **Admin:** `GET /admin/analytics`

## 7. User journey
1. 18+ gate and consent.
2. "What's broken?" Category tile, camera, text or voice.
3. Label OCR, then confirm the model.
4. Safety card (may stop here).
5. Question cards with a live cause chart.
6. Diagnosis: tier label, confidence and evidence for each cause.
7. Guide: confirm the safety checklist, then steps, tools, time and ₹, then "Did it work?"
8. **Parts:** the required spec is shown. Offers from multiple retailers with price, stock and "last checked". Each offer has a match badge. Add to cart.
9. **Cart:** grouped by retailer, with the affiliate disclosure, then "Checkout on Amazon / Flipkart".
10. Nearby help.
11. Outcome, prevention tips, reminder, history.

Follow-up chat is available throughout. EN/HI toggle. Mobile-first.

## 7b. UI/UX: startup-grade, clean, simple, dynamic
**Principles:**
- Calm confidence, because a broken appliance is stressful.
- One primary action per screen.
- Progressive disclosure: simple first, "Why?" one tap away.
- Trust made visible: tier badges, sources, timestamps.
- Safety visually unmistakable.
- Thumb-zone mobile layout.
- Fast on mid-range Android over 4G.
- Bilingual by design.

**Brand and visual system (design tokens, light and dark mode):**
- **Voice:** a friendly expert, like a knowledgeable friend who's also a technician. Short sentences, no jargon unless explained.
- **Colour:** a deep teal/indigo primary for trust, a warm amber accent for actions. Semantic colours: Verified green, Likely blue, AI-suggestion grey, Caution amber, STOP red. Every colour passes WCAG AA contrast.
- **Type:** Inter (Latin) + Noto Sans Devanagari (Hindi), from Google Fonts. Devanagari gets taller line-height. Fluid type scale.
- **Shape:** 8-pt spacing, 12–16 px radius, soft layered shadows, generous whitespace.
- **Icons and illustrations:** Lucide icons, plus a custom line-illustration set for the ~50 components (capacitor, jack, solder joint…). Illustrations are reused in guides.

**Motion (dynamic, but never decorative noise):**
- The cause chart re-ranks with spring animation as each answer narrows the posterior. This is the signature interaction.
- Shared-element transitions between question cards and guide steps.
- Camera scanning reticle that snaps to the detected label box.
- Live voice waveform.
- Streaming answer text with skeleton loaders.
- Success confetti when a repair is verified.
- Haptics on Android (`navigator.vibrate`) for STOP and success.
- Everything respects `prefers-reduced-motion`.

**Key screens:**
1. **Marketing site:**
   - Hero with a looping product demo.
   - "How it works" in 3 steps.
   - A **reliability section** showing real FixBench-IN numbers (filled in only from real runs).
   - Safety promise, category grid, testimonials only once real ones exist, FAQ, footer with disclosures.
2. **Home:** one large "What's broken?" input with camera, mic and text. Category chips. "Continue your repair" cards.
3. **Live camera:** full-bleed camera with an AR-style overlay: detected item chip, "Point at the rating label" coach marks, capture button. Privacy indicator ("Faces blurred · Nothing sent until you tap").
4. **Diagnosis:** a conversational timeline with structured cards inline (question chips, photo requests, multimeter test cards), not a plain chat. The collapsible live cause panel shows probability bars, with words alongside ("Very likely / Possible").
5. **Guide player:** full-screen steps with large illustrations, swipe or voice "next", timers, a tool checklist and a progress ring. **Hands-free mode**, since your hands are dirty. Works offline once loaded, through the PWA cache.
6. **STOP screen:** full-screen red, haptic. Immediate actions, a 112 call button, "Find a professional".
7. **Parts and offers:** spec header ("2.5 µF · 440 V · CBB61"). Offer cards show price, stock, "checked 2 h ago", match badge and retailer name. Sort and filter. Price-trend sparkline (non-Amazon sources).
8. **Cart:** grouped by retailer, with savings and totals in ₹. "Checkout on Flipkart / Amazon" handoff. Disclosure inline.
9. **Nearby:** MapLibre GL map with free OSM-based vector tiles (provider confirmed at R8), plus a list view with call buttons.
10. **History and profile:** repair timeline, savings tracker ("₹ saved vs a call-out", estimated and labelled as such), reminders, language, data controls.
11. **Admin and analytics dashboard:** outcomes, funnel, benchmark trends.
12. **Empty, error, offline and "API waking up" states,** each designed with care, plus a friendly quota-busy state.

**UX details:**
- An "Explain why" on every claim opens its source.
- Undo on answers.
- Optimistic UI.
- Skeletons instead of spinners.
- Command-style search.
- Onboarding of 3 swipeable cards at most.
- Low-literacy support: icons, images, read-aloud on every card.

**Accessibility and performance budgets:**
- WCAG 2.1 AA: 44 px touch targets, full keyboard and screen-reader support.
- Lighthouse ≥90 on performance, accessibility and best practices; axe clean in CI.
- LCP under 2.5 s on a mid-range Android over 4G.
- ML models (ONNX, Tesseract) are lazy-loaded only when the camera opens.
- JS bundle budget enforced in CI.

**Libraries:**
- Next.js static export, Tailwind v4, shadcn/ui on Radix (accessible primitives).
- Motion (Framer Motion) for animation.
- Lucide icons.
- Recharts for dashboards and sparklines.
- MapLibre GL for maps.
- next-intl for EN/HI.
- Storybook for the component library and visual review.

**Design process:**
1. Moodboard and design tokens.
2. High-fidelity **clickable prototype** of the key screens: Home, Camera, Diagnosis, Guide, STOP, Parts, Cart. Built in Figma (Figma connector available) or as a coded prototype, for **your approval before building screens**.
3. A 5-person hallway usability test (family and friends, EN and HI).
4. Iterate.
5. Lock the component library in Storybook.

## 8. Safety, reliability, privacy, commerce integrity
**Safety:**
- Deterministic gate plus FT-1. Hard-block triggers: gas or LPG smell, burning smell, smoke, sparks, shock, water near live parts, refrigerant, geyser, wiring/MCB, RO UV lamp, opening SMPS adapters, swollen Li-ion.
- The response is a STOP card with immediate actions, emergency number 112 (the LPG helpline will be verified before it ships) and the professional route.
- **Family-specific rules:**
  - Fan capacitor: MCB off, safe ladder use, discharge, match µF and voltage.
  - Extension board: work only when unplugged; replace if burnt or melted; ISI-marked parts.
  - Toys: button-cell swallowing hazard, glove up for electrolyte, keep children away.
  - Soldering: burns, fumes, ventilation.
- **Levels:** 0 safe; 1 unplug; 2 isolate + PPE (Tier A/B, KG-verified only); 3 professional only. Tier C is capped at level 1. The output validator replaces any over-level steps.
- A red-team suite runs in CI, and the release gate is full blocking on the hard-block set.

**Reliability:**
- Every claim is labelled Verified, Likely or AI suggestion.
- Claims must be cited in Tiers A and B.
- Calibrated abstention.
- The engine-only fallback runs when quota is exhausted.

**Privacy (Gemini free tier):**
- Consent notice that Google may use inputs and human reviewers may read them.
- 18+ only.
- On-device crop, face blur, EXIF strip and downscale. Frames are sent only on tap.
- OCR and speech-to-text run locally, and we disclose Chrome's server-side speech recognition. Typing is always available.
- A PII scrubber runs on text. Name, email and location never go to Gemini.
- No image storage by default. `DELETE /me/data`.
- DPDP-aligned privacy policy.
- A config flag switches to the $5 prepaid tier.

**Commerce integrity:**
- No price is shown without a provider source and a `fetched_at` time.
- Amazon prices come from the Creators API only, with a timestamp when older than one hour.
- No "compatible" claim without a spec match backed by evidence. Otherwise "Unverified — check X".
- Out of stock or stale data is shown as such.
- Affiliate disclosures (Amazon Associates statement, ASCI-style material-connection notice).
- Ranking is by spec match, then price. Commission never affects ranking, and this is stated publicly.
- Terms of use with a liability disclaimer.

## 9. Release roadmap (each release deployed; working end-to-end from R1)
| Release | Contents | Acceptance |
|---|---|---|
| R0 Foundations | Monorepo (`apps/web`, `apps/api`, `kb/`, `ingest/`, `ml/`, `eval/`, `osm/`), CI, Supabase, Cloudflare Pages + Render, `LLMProvider` (Gemini/Ollama). Confirm Gemini limits, Cloudflare commercial terms, Render RAM | Deployed hello-world, CI green, constraints recorded |
| R0.5 Design sprint | Moodboard, tokens, clickable hi-fi prototype of 7 key screens (Figma or coded), usability test with 5 people, Storybook component library, marketing-site design | **You approve the prototype.** Tokens and components in Storybook. Lighthouse/axe CI checks set up |
| R1 Walking skeleton | Text session for one family (ceiling fan): extractor, small engine, 3 procedures, safety gate v1, outcome | End-to-end session in production. Hard-block tests pass |
| R2 Knowledge graph + engine + benchmark | ~50 components; fans, extension boards, audio, toys; Tier-B mapping; info-gain; FixBench-IN v1; baseline (a); FT-1 | Report with (a) vs (d). FT-1 recall reported |
| R3 Verified RAG | Ingestion, hybrid retrieval, claim verification, self-consistency, calibration, Tier C | (b)/(c) measured. No uncited A/B claims |
| R4 Vision + OCR | Camera, privacy filter, Tesseract, classifier → ONNX, live hint | Classifier and OCR metrics, on-device latency |
| R5 Voice + Hindi | Speech-to-text and text-to-speech, Hindi UI and prompts, Hindi eval | Hindi session works. F1 reported |
| R6 Commerce I | Join Amazon Associates and Flipkart Affiliate as an individual (PAN). Part-spec resolver, Flipkart adapter, SerpApi scheduled refresh, attribute extractor, spec matcher, offers UI with timestamps | Live prices and stock shown with sources. Matcher precision measured on a labelled listing set |
| R7 Commerce II | Cart, checkout handoff (Amazon multi-item cart-add link if amazon.in Associates supports it, otherwise per-product links; Flipkart links), disclosures, handoff analytics. Amazon Creators API adapter switched on once eligible | Handoff works on both retailers. Compliance checklist done |
| R8 Appliances + places | Washer, plumbing, RO families; OSM PostGIS; nearby; service-centre links; prevention and reminders | FixBench-IN extended. Map attribution |
| R9 Accounts + analytics | Google sign-in, history, delete-my-data, admin dashboards (outcomes, funnel, price trends), prior updating | RLS verified. Real data only |
| R10 Fine-tuning research | FT-2 verifier deployed, FT-3 Gemma QLoRA evaluated, model cards | (e) published |
| R11 Live + damage | Gemini Live streaming mode (ephemeral tokens), damage classifier from consented data | Quota-safe live sessions. Classifier metrics |
| R12 Hardening + launch | Red-team expansion, rate limits, Sentry, backups, legal pages, load test, public launch | §10 checklist complete |

## 10. Testing, deployment, production readiness
- **Tests:**
  - pytest: engine maths, safety rules, PII scrubber, parsers, spec matcher, provider adapters with recorded responses.
  - API contract tests.
  - Playwright end-to-end tests on a mobile viewport: diagnose, guide, parts, cart, handoff.
  - Eval harness on fixtures in CI, live runs manual.
  - Light load test.
- **Deployment:** Cloudflare Pages (web), Render Docker (API), Supabase migrations in the repo, secrets in platform env vars.
- **Operations:**
  - Logging: JSON logs with request IDs, plus audit tables for LLM and provider calls.
  - Errors: Sentry.
  - Monitoring and backups: health checks and a weekly scheduled smoke test, which also prevents the Supabase pause; weekly `pg_dump` via GitHub Actions.
  - Security: CORS, rate limits, input limits, RLS.
  - Cost controls: provider quota budgets (SerpApi monthly counter, Gemini per-user caps).
- **Honest limits of the free-tier product:**
  - API cold starts.
  - Shared Gemini quota and free-tier data terms.
  - 500 MB DB, no point-in-time recovery.
  - Live data limited by the free quotas (prices can be hours old, always shown as such).
  - Amazon prices only after 10 sales in 30 days.
- **Scaling path when revenue allows:** paid Gemini, always-on API, Supabase Pro, SerpApi Starter, legal review, technician-reviewed KB.

## 11. Costs and dependencies
| Item | Cost |
|---|---|
| Gemini free, Cloudflare Pages, Render free, Supabase free, Sentry free, Colab/Kaggle, OSM, GitHub, Flipkart and Amazon affiliate programs, SerpApi free | ₹0 |
| Optional: Gemini $5 prepaid (hard stop) | About ₹450, only if needed |
| Optional: domain | Free subdomain until revenue |

**Dependency risks:**
- Free-tier limit changes.
- Flipkart API status.
- The Amazon 10-sale threshold.
- SerpApi's 100 searches a month.
- Patchy OSM coverage.
- TDS and income-tax reporting on affiliate income as an individual. This is your responsibility.

## 12. Resume and demo
**Headline:** "Built FixBench-IN and a verified-generation pipeline: unsupported-claim rate X%→Y%, safety-critical errors A→B vs vanilla Gemini." Filled in only from real runs.

**Also reported:** engine Top-3, FT-1 recall, Recall@5, classifier F1/latency/size, OCR exact match, spec-match precision, questions to diagnosis, ₹0 per session, real outcomes and handoff conversions if any.

**Demo (4 min):**
1. Point a phone at a ceiling fan that's humming but won't spin. The live hint appears.
2. The engine asks two questions, then gives a capacitor diagnosis with citations.
3. Safety checklist, then the guide.
4. The parts finder shows 2.5 µF/440 V listings with live price, stock, match badges and timestamps.
5. Cart, then handoff to Flipkart.
6. "I smell burning" brings up the STOP card.
7. A Hindi voice session on headphones.
8. The FixBench-IN report and the dashboard.

Ship it with a README, an architecture document, model cards and eval reports.

## Verification
- Each release's acceptance criteria are checked on the deployed app with pytest, Playwright and the `eval/` reports.
- No release ships unless the safety suite passes.
- No price is ever shown without a source and a timestamp.
