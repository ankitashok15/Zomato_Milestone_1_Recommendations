# AI-Powered Restaurant Recommendation System
## Detailed Phase-Wise Architecture

This document provides a detailed, implementation-oriented architecture for building an AI-powered restaurant recommendation system inspired by Zomato, based on the provided problem statement.

---

## 0) Target System Blueprint (Reference)

### Core flow
1. User submits preferences from UI.
2. Backend validates and normalizes preferences.
3. Candidate retrieval service filters restaurants from structured store.
4. Ranking pipeline computes deterministic scores.
5. LLM reranks top candidates and generates natural-language explanations.
6. API returns top recommendations and metadata.
7. User feedback is captured for model and prompt improvements.

### Core services
- `frontend-app`: Collect preferences and render recommendations (see **dual UX** below).
- `api-gateway`: Public API surface for clients.
- `preference-service`: Validation and normalization.
- `catalog-service`: Restaurant data ingestion, cleaning, and querying.
- `retrieval-service`: Candidate selection and pre-ranking.
- `llm-orchestrator`: Prompt construction, LLM calls, output parsing.
- `recommendation-service`: End-to-end recommendation pipeline.
- `feedback-service`: Store user reactions and outcomes.
- `observability-stack`: Logs, metrics, traces, alerts.

### Data stores
- `PostgreSQL` (primary structured restaurant data and audit tables)
- `Redis` (query/result cache)
- Optional: `Vector DB` (for semantic matching from free-text preferences)
- Object storage for raw/processed dataset versions.

### Dual UX delivery (web)
Two browser clients can talk to the same Phase 6 FastAPI service:

| Layer | Path in repo | How it runs | API access |
|--------|----------------|-------------|------------|
| **Legacy static UI** | `frontend/` | Served by FastAPI at **`GET /ui`** (and `/static/*` assets) | Same origin as API: direct `fetch` to `/ui-api/*`, `/health/detailed`, etc. |
| **Next.js enhanced UI** | `frontend-next/` | **`npm run dev`** (default **http://localhost:3000**) in dev; `npm run build` + `npm start` for production-style | Browser calls **`/api/backend/*`** only; **Next.js rewrites** that prefix to **`BACKEND_URL`** (e.g. `http://127.0.0.1:8010`) so the browser never cross-origin calls FastAPI (no CORS changes required). |

**Next.js app responsibilities (high level):**
- **Home**: locality + cuisine pickers (with search/filter for large catalogs), preference form, `POST /ui-api/recommendations`, results, `POST /ui-api/feedback/{click|like|not_relevant}`, optional `GET /health/detailed`.
- **History**: reads/writes browser **`localStorage`** key **`zomato_request_history`** — same contract as the legacy UI so history is portable between clients on the same machine/browser.
- **Metrics**: `GET /health/detailed` and `GET /ui-api/metrics` for ops visibility.

**Design system:** UI tokens and patterns follow `Docs/Improvements.md/Design.md` (primary `#E23744`, secondary `#2D2D2D`, tertiary `#008881`, typography Epilogue + Plus Jakarta Sans, card/search/chip patterns).

**Resilience:** Client `fetch` uses bounded timeouts when calling the Next proxy so a down or misconfigured backend fails fast instead of hanging the tab; large locality/cuisine lists are windowed/filtered in the UI to avoid main-thread stalls.

---

## Phase 1: Requirements, Domain Modeling, and Success Metrics

### Objective
Translate business problem into technical contracts and measurable outcomes.

### Deliverables
- Functional requirement spec.
- Domain model and entity relationships.
- Recommendation quality KPIs and non-functional requirements.

### Architecture work
- Define entities:
  - `Restaurant`
  - `Cuisine`
  - `City/Locality`
  - `PriceBand`
  - `UserPreference`
  - `RecommendationResult`
  - `FeedbackEvent`
- Define success metrics:
  - Precision@K on benchmark prompts.
  - User satisfaction score.
  - P95 latency and cost/request.
- Define non-functional targets:
  - P95 API latency <= 2.5s for cached queries, <= 6s uncached.
  - Availability target (e.g., 99.5%).
  - Explainability in every recommendation item.

### Exit criteria
- Signed-off data contract for input/output payloads.
- Baseline KPI targets agreed before implementation.

---

## Phase 2: Data Ingestion and Standardization Layer

### Objective
Create a reliable, queryable restaurant catalog from the Hugging Face Zomato dataset.
Dataset link: https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation

### Components
- `ingestion-job` (scheduled or one-time batch)
- `schema-mapper`
- `data-quality-validator`
- `catalog-loader`

### Detailed pipeline
1. Pull dataset snapshot from Hugging Face.
2. Persist raw snapshot to object storage (`raw/YYYY-MM-DD/`).
3. Map source fields to canonical schema.
4. Normalize values:
   - Location canonicalization (`Bangalore` vs `Bengaluru` rules)
   - Cuisine token normalization (split/join multi-cuisine strings)
   - Cost normalization to numeric + currency + `price_band`
   - Rating normalization to `0-5` float range.
5. Run quality checks:
   - Null critical fields
   - Outlier costs/ratings
   - Duplicate restaurant records.
6. Upsert into `restaurants` tables.

### Suggested schema (logical)
- `restaurants(id, name, locality, city, latitude, longitude, avg_cost_for_two, price_band, rating, votes, is_active, updated_at)`
- `restaurant_cuisines(restaurant_id, cuisine)`
- `restaurant_tags(restaurant_id, tag)` (optional, from enrichment)
- `dataset_runs(run_id, source_version, records_total, records_loaded, quality_report, created_at)`

### API/contract outputs from this phase
- Internal query contract for retrieval:
  - by city/locality
  - by cost band
  - by minimum rating
  - by cuisine list.

### Exit criteria
- Data completeness and quality thresholds met.
- Query benchmarks pass (index-backed lookups under target latency).

---

## Phase 3: Preference Capture and Input Intelligence

### Objective
Capture user intent in a structured and model-friendly format.

### Components
- UI preference form + optional conversational input.
- `preference-service` for validation and normalization.
- Input parser for optional free-text constraints.

### Input contract
- Required:
  - `location`
  - `budget_amount` (integer INR: max acceptable cost for two people; retrieval uses range `0..budget_amount`)
  - `cuisine` (single or list)
  - `min_rating`
- Optional:
  - `party_type` (`family`, `friends`, etc.)
  - `service_expectation` (`quick_service`)
  - `dietary_preference`
  - `free_text_notes`.

### Processing steps
1. Validate fields and ranges.
2. Normalize:
   - Budget -> numeric cost range from `budget_amount` (`min=0`, `max=budget_amount` INR).
   - Cuisine aliases -> canonical cuisine tokens.
   - City/locality -> canonical location entities.
3. Parse free text:
   - Extract intents/tags with lightweight NLP or LLM-mini pass.
4. Produce final normalized preference object.

### Exit criteria
- Invalid inputs correctly rejected with actionable messages.
- >= 95% of typical user variations mapped to canonical values.

---

## Phase 4: Candidate Retrieval and Deterministic Ranking

### Objective
Efficiently reduce full catalog to high-quality candidates before LLM use.

### Components
- `retrieval-service`
- SQL query builder and optional feature store
- deterministic scoring module.

### Retrieval strategy
- Hard filters:
  - City/locality match
  - Rating >= min_rating
  - Cost within numeric budget (`avg_cost_for_two` between `0` and user `budget_amount` INR)
- Soft filters:
  - Cuisine overlap score
  - Tag overlap from optional preferences.

### Pre-ranking score (example)
- `score = 0.35*rating + 0.30*cuisine_match + 0.20*budget_fit + 0.15*popularity`
- Normalize all components to `[0,1]`.
- Select top `N` (20-50) as LLM candidates.

### Performance architecture
- Indexes:
  - `(city, price_band, rating)`
  - GIN/text index for cuisines (if needed)
- Cache frequent queries in Redis with normalized query key hash.

### Exit criteria
- Stable and relevant top-N candidate sets.
- Retrieval P95 under target (e.g., < 300ms on warm cache).

---

## Phase 5: LLM Orchestration and Explainable Recommendation

### Objective
Use LLM for nuanced reranking and human-like explanations, constrained by structured input.

### Components
- `llm-orchestrator`
- `Groq LLM` (provider for inference in Phase 5)
- prompt templates (versioned)
- output schema validator
- fallback policy manager.

### Prompt architecture
- System instruction:
  - Only use provided candidates.
  - Return strict JSON.
  - Rank top K.
  - Explain fit against user preferences and trade-offs.
- Context payload:
  - normalized user preference
  - top-N candidate list (compact structured records)
- Output schema:
  - `restaurant_id`
  - `rank`
  - `fit_score` (0-100)
  - `explanation`
  - `cautions` (optional).

### Guardrails
- JSON schema validation + retries.
- Hallucination prevention:
  - reject unknown `restaurant_id`.
- Fallback:
  - If LLM fails, return deterministic top-K with template explanations.

### Cost/latency controls
- Cap candidate count in prompt.
- Use compact serialization and prompt compression.
- Cache recommendation responses for repeated normalized queries.

### Exit criteria
- Valid schema output rate >= 99%.
- Explanation quality rated acceptable in evaluation set.

---

## Phase 6: Recommendation API, UX Delivery, and Feedback Capture

### Objective
Serve recommendations reliably and present them clearly in product UI.

### Components
- `recommendation-service` API
- **Two** web UIs: legacy static bundle under `frontend/` and optional **Next.js** app under `frontend-next/` (shared backend contracts)
- feedback collection endpoints

### Primary API
- `POST /recommendations`
  - Request: user preference payload.
  - Auth/config: API key is stored in `.env` and loaded via environment variable.
  - Response:
    - `request_id`
    - `top_recommendations[]`:
      - restaurant name
      - cuisine
      - rating
      - estimated cost
      - AI explanation
    - `summary` (optional)
    - `debug` block in non-prod.

### Feedback APIs
- `POST /feedback/click`
- `POST /feedback/like`
- `POST /feedback/not_relevant`

### Catalog read APIs (dropdowns)
- UI (no API key): `GET /ui-api/localities`, `GET /ui-api/cuisines`.
- Authenticated parity: `GET /localities`, `GET /cuisines` (same payloads).

### UX architecture guidelines
- Show concise recommendation reason first.
- Surface key fields consistently (rating, cost, cuisine, locality).
- Add lightweight transparency note: "AI-assisted ranking from available restaurants."
- **Legacy home UI** (`/ui`): locality dropdown (`GET /ui-api/localities`), cuisine multi-select from catalog (`GET /ui-api/cuisines`), numeric budget field (`budget_amount`); browser calls `POST /ui-api/recommendations` without manual API key entry.
- **Next.js home** (`frontend-next`): same API semantics; requests go to **`/api/backend/...`** and are proxied server-side to FastAPI. Configure **`BACKEND_URL`** (see `frontend-next/.env.local.example`). Optional **History** and **Metrics** routes mirror `frontend/assets/history.js` and `frontend/assets/metrics.js` behavior.

### Exit criteria
- End-to-end user journey complete and testable.
- Feedback events captured with traceable request linkage.

---

## Phase 7: Evaluation Framework and Continuous Improvement

### Objective
Measure recommendation quality and iteratively improve retrieval + prompting.

### Components
- offline evaluation dataset
- prompt experiment framework
- analytics dashboards.

### Evaluation layers
- Offline:
  - curated query set with expected outcomes.
  - precision@K, NDCG, explanation usefulness rubric.
- Online:
  - CTR, save-rate, session satisfaction.
  - abandonment rate after recommendation view.

### Experimentation
- A/B test:
  - Prompt template versions
  - Weighting in deterministic scorer
  - Candidate set size.

### Exit criteria
- Data-driven process for model/prompt updates in place.
- Monthly quality trend visible on dashboards.

---

## Phase 8: Production Hardening, Security, and Scale

### Objective
Operate safely and cost-effectively in production.

### Components
- auth/rate-limiting middleware
- secret management
- autoscaling + circuit breakers
- incident response playbooks.

### Reliability architecture
- Timeouts and retries for external LLM calls.
- Circuit breaker for model outages.
- Queue-based retry for non-critical async operations.
- Graceful degradation to non-LLM ranking.

### Security architecture
- API key/JWT auth (depending on product model).
- Input sanitization and abuse detection.
- PII minimization in logs and prompts.
- Secrets in vault, not code/config files.

### Scalability architecture
- Horizontal scale stateless APIs.
- Redis caching for hot routes.
- Read replicas for heavy retrieval reads.
- Optional vector service split if semantic matching grows.

### Exit criteria
- Runbook-tested failover and recovery.
- Security checklist and load tests passed.

---

## Cross-Cutting Architecture Decisions

### Tech stack (recommended)
- Backend: `Python (FastAPI)` or `Node.js (NestJS/Express)`
- **Web (enhanced)**: `Next.js` (App Router) + TypeScript in `frontend-next/`, calling FastAPI via dev/prod rewrite proxy
- **Web (legacy)**: static HTML/JS under `frontend/` served by FastAPI
- Data processing: `Pandas + SQLAlchemy` (Python path)
- DB: `PostgreSQL`
- Cache: `Redis`
- LLM provider via abstraction layer to avoid vendor lock-in.

### Versioning strategy
- Version:
  - dataset snapshot
  - prompt templates
  - recommendation algorithm weights
  - API contracts.

### Observability
- Metrics:
  - request latency by stage
  - LLM token/cost metrics
  - cache hit ratio
  - error rates and schema-parse failures.
- Tracing:
  - `request_id` propagated across services.

### Governance
- Prompt changes gated via review.
- Regression suite required before rollout.
- Feature flags for controlled rollout.

### Deployment (target platform summary)
- **Frontend:** Vercel — Next.js app in `frontend-next/`.
- **Backend:** Streamlit — Streamlit Community Cloud (or equivalent managed Streamlit hosting) for the Python-side delivery defined by the product team.

---

## Deployment architecture (target platform)

This section records the **intended production topology**: Next.js on **Vercel**, Python backend on **Streamlit**. It also ties that choice to the **current reference implementation** (FastAPI + Next `BACKEND_URL`).

### Frontend — Vercel

| Topic | Guidance |
|--------|-----------|
| **Project** | Deploy from Git; set the Vercel project **root** to `frontend-next/` (or use a monorepo “Root Directory” setting pointing at that folder). |
| **Build** | Install with `npm install`; production build `npm run build`; start command `npm run start` (default for Next.js on Vercel). |
| **Environment variables** | Set **`BACKEND_URL`** to the **public HTTPS origin** of the live API (example: `https://api.example.com`), **no** trailing path. The app rewrites browser calls from `/api/backend/*` to `${BACKEND_URL}/*` on the server. |
| **Networking** | End users only load pages from the Vercel domain; API calls are proxied by Next.js, so the browser does not need direct CORS access to the API origin for that path. |
| **Optional** | Preview deployments: use a staging `BACKEND_URL` or branch-specific env in Vercel. |

### Backend — Streamlit (Streamlit Community Cloud)

| Topic | Guidance |
|--------|-----------|
| **Platform** | **Streamlit Community Cloud** (or enterprise Streamlit hosting): connect the Git repository; main file **`streamlit_app.py`** (repo root); Python packages file **`requirements-streamlit.txt`**; **Secrets** e.g. `GROQ_API_KEY`, optional `GROQ_MODEL` (never commit `.env`). |
| **Secrets** | Map production secrets (e.g. LLM keys, optional DB URLs) via the host’s secret manager / `st.secrets` pattern expected by Streamlit. |
| **Artifacts** | Ensure processed catalog data and any models required at runtime are available to the deployed environment (bundle in repo where appropriate, or download from object storage on startup with guarded credentials). |

#### Alignment with the current FastAPI + Next.js stack

The reference backend in this repo is **`phase6` FastAPI** (`uvicorn`), which exposes **HTTP JSON** routes (`/ui-api/*`, `/health/detailed`, etc.). **Streamlit Cloud** is built to run **`streamlit run <app>`** and serve an interactive Streamlit UI; it does **not** by itself replace that HTTP contract for **`BACKEND_URL`**.

**Recommended architecture patterns:**

1. **Dual Python surfaces (common)**  
   - Keep or deploy **FastAPI** on an **ASGI-capable** host (e.g. Render, Railway, Fly.io, Google Cloud Run, AWS App Runner) as the **`BACKEND_URL`** for Vercel.  
   - Deploy **Streamlit** separately for analytics, internal tooling, or alternate UX that **imports the same** `phase3`–`phase5` (and data) modules. Both share one codebase; two deploy targets.

2. **Streamlit-only product path**  
   - If the product standardizes on Streamlit for all user-facing Python UX, the **Next.js** app on Vercel either needs a **still-reachable HTTP API** (see pattern 1) or is phased out in favor of Streamlit URLs—**not** a drop-in swap for `BACKEND_URL` without new engineering.

Document the chosen pattern in the runbook so **`BACKEND_URL`** on Vercel always points at an origin that actually serves the `/ui-api/*` contract (or an updated contract if the API is versioned).

### End-to-end checklist (Vercel + API)

- [ ] Vercel: `BACKEND_URL` set and verified (smoke `GET /health` or `/health/detailed` from the deployment pipeline).
- [ ] API: HTTPS, stable hostname, rate limits and auth consistent with Phase 8.
- [ ] Streamlit (if used): secrets and data paths validated on Community Cloud; role documented (public app vs internal tool vs companion to FastAPI).

---

## Suggested Implementation Milestones (Execution Plan)

Implementation note: complete backend phases first (Phase 1 through Phase 6 core API), then iterate UI and hardening. The **Next.js** client in `frontend-next/` is the preferred surface for future UX work; the **static** UI remains the zero-dependency path served from FastAPI.

1. Build dataset ingestion + normalized schema + query indexes.
2. Build preference API + retrieval/pre-ranking endpoint.
3. Add LLM orchestration with schema-validated output and fallback.
4. Integrate recommendation UI and feedback capture (static UI + optional Next.js app sharing `/ui-api/*` contracts).
5. Add observability, caching, and quality dashboards.
6. Launch A/B tests and optimize ranking/prompt quality.
7. Harden for production (security, reliability, scaling).

---

## Definition of Done (Project-Level)

- User can submit preferences and get top recommendations with explanations (via **FastAPI `/ui`** and/or **`frontend-next`** with `BACKEND_URL` pointed at the API).
- Every recommendation item includes name, cuisine, rating, estimated cost, and AI rationale.
- System meets latency, reliability, and quality thresholds.
- Monitoring, feedback loops, and fallback behavior are production-ready.
