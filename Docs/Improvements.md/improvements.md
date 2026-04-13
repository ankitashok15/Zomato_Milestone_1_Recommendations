# Product improvements (implemented)

These items from the original improvement notes are now reflected in backend, frontend, and `phase_wise_architecture.md` (surgical updates only).

## 1. Budget: numeric value (not low / medium / high)

- **Backend:** `PreferenceInput.budget_amount` (INR, max acceptable cost for two). Normalized `budget_range` is `min_cost_for_two=0`, `max_cost_for_two=budget_amount`.
- **Frontend:** Single number field “Max budget (INR, cost for two)”.
- **API:** Request JSON uses `budget_amount` (integer), not `budget`.

## 2. Cuisine: dropdown from catalog

- **Backend:** `GET /ui-api/cuisines` and `GET /cuisines` (authenticated) return distinct cuisines from processed data; `RetrievalService.list_cuisines()`.
- **Frontend:** Multi-select `<select id="cuisine" multiple>` populated from `/ui-api/cuisines` (Ctrl/Cmd multi-select).
- **Next.js (`frontend-next/`):** Same endpoints via `/api/backend` rewrite; checkbox grid with optional text filter for large catalogs. Design tokens: `Docs/Improvements.md/Design.md`.

## 3. Next.js client (optional enhanced UI)

- **Run:** `npm run dev` in `frontend-next/` (port 3000); set `BACKEND_URL` to the FastAPI base URL.
- **Routes:** Home (recommendations + feedback), History (`localStorage` key `zomato_request_history`, shared with legacy UI), Metrics (`/health/detailed`, `/ui-api/metrics`).
- **Architecture:** See **Dual UX delivery** and Phase 6 updates in `phase_wise_architecture.md`.

## Reference

- Architecture: Phase 3 (input contract), Phase 4 (cost filter), Phase 6 (UX + dual delivery + Next proxy).
- Phase 1 contracts: `phase1/data_contracts.md`, `phase1/domain_model.md`, `phase1/functional_requirements.md`.
