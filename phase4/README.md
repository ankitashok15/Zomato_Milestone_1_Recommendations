# Phase 4 Implementation: Candidate Retrieval and Deterministic Ranking

This phase implements the `retrieval-service` and deterministic pre-ranking module using Phase 2 processed data.

## Implemented capabilities
- Hard filters:
  - city/locality match
  - `rating >= min_rating`
  - `avg_cost_for_two` within budget range
- Soft scores:
  - cuisine overlap score
  - tag overlap score
  - budget fit score
  - popularity score (normalized votes)
- Final deterministic score:
  - `0.35*rating + 0.30*cuisine_match + 0.20*budget_fit + 0.15*popularity`
- Returns top `N` candidates (default 30).
- In-memory cache for repeated normalized retrieval requests.

## API entrypoint (Phase 3 + Phase 4)
- `phase4/src/api.py`
- Endpoints:
  - `POST /phase3/normalize`
  - `POST /phase4/candidates`
  - `POST /phase4/normalize-and-candidates`

## Run API
```powershell
python -m pip install -r phase4/requirements.txt
uvicorn phase4.src.api:app --reload --port 8000
```
