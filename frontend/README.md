# Basic Frontend UI

This folder contains a minimal browser UI for end-to-end backend testing.

## How to run
Start backend API server:

```powershell
uvicorn phase6.src.recommendation_api:app --reload --port 8000
```

Open in browser:

- Home: `http://127.0.0.1:8000/ui` (localities: `GET /ui-api/localities`; cuisines: `GET /ui-api/cuisines`; numeric `budget_amount`)
- History: `http://127.0.0.1:8000/static/history.html`
- Metrics: `http://127.0.0.1:8000/static/metrics.html`

## Features
- Home page: preferences form, recommendations, feedback actions.
- History page: local session request history (from browser localStorage).
- Metrics page: `health/detailed` and `internal/metrics` view.
