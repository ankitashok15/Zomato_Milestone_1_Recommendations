# Phase 6 Implementation: Recommendation API, UX Delivery, and Feedback Capture

This phase exposes production-style endpoints for recommendation serving and feedback collection.

## Implemented capabilities
- `POST /recommendations`
  - accepts user preference payload
  - runs Phase 3 normalization
  - runs Phase 4 candidate retrieval
  - runs Phase 5 LLM reranking + explanation
  - returns top recommendations with required fields
- API key protection using `.env` value:
  - `RECOMMENDATION_API_KEY`
  - read via `X-API-Key` request header
- Feedback endpoints:
  - `POST /feedback/click`
  - `POST /feedback/like`
  - `POST /feedback/not_relevant`
- Feedback events persisted to JSONL:
  - `phase6/data/feedback_events.jsonl`

## Files
- `phase6/src/recommendation_api.py`
- `phase6/requirements.txt`

## Run
```powershell
python -m pip install -r phase6/requirements.txt
uvicorn phase6.src.recommendation_api:app --reload --port 8000
```

## Example call
Include API key header:
- `X-API-Key: <your RECOMMENDATION_API_KEY>`
