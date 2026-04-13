# Data Contracts (Phase 1)

This file defines contract-first payloads to be implemented in later phases.

## 1. User Preference Request Contract

```json
{
  "location": "Indiranagar",
  "budget_amount": 1800,
  "cuisine": ["Italian", "Continental"],
  "min_rating": 4.0,
  "additional_preferences": "family-friendly and quick service"
}
```

### Validation rules
- `location`: required, non-empty string.
- `budget_amount`: required, integer INR (e.g. `50..100000`), max acceptable cost for two.
- `cuisine`: required, non-empty array of strings (or a single string accepted by the API).
- `min_rating`: required, number in `0.0..5.0`.
- `additional_preferences`: optional, max recommended length 300 chars.

## 2. Normalized Preference Contract (Internal)

```json
{
  "request_id": "req_2026_04_13_0001",
  "normalized_location": {
    "city": "Bengaluru",
    "locality": null
  },
  "budget_amount": 1800,
  "budget_range": {
    "min_cost_for_two": 0,
    "max_cost_for_two": 1800,
    "currency": "INR"
  },
  "canonical_cuisines": ["italian", "continental"],
  "min_rating": 4.0,
  "derived_tags": ["family-friendly", "quick-service"]
}
```

## 3. Recommendation Response Contract

```json
{
  "request_id": "req_2026_04_13_0001",
  "summary": "Top picks balancing your cuisine preference and budget.",
  "top_recommendations": [
    {
      "rank": 1,
      "restaurant_id": "res_123",
      "restaurant_name": "Olive Bistro",
      "cuisine": ["Italian", "Continental"],
      "rating": 4.4,
      "estimated_cost_for_two": 1500,
      "currency": "INR",
      "ai_explanation": "Strong Italian options, within your medium budget, and known for family seating."
    }
  ]
}
```

### Response guarantees
- `top_recommendations` is ordered by `rank`.
- `rank` starts at `1`.
- Every item includes a non-empty `ai_explanation`.
- Every `restaurant_id` must exist in catalog.

## 4. Feedback Event Contract

```json
{
  "feedback_id": "fb_00001",
  "request_id": "req_2026_04_13_0001",
  "restaurant_id": "res_123",
  "event_type": "like",
  "event_value": "good-for-family"
}
```

### Event types
- `click`
- `like`
- `not_relevant`

## 5. Dataset Run Contract

```json
{
  "run_id": "run_2026_04_13_01",
  "source_name": "huggingface_zomato_recommendation",
  "source_url": "https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation",
  "source_version": "snapshot_2026_04_13",
  "records_total": 10000,
  "records_loaded": 9875,
  "quality_report": {
    "missing_rating": 42,
    "duplicate_records": 83
  }
}
```
