# Phase 3 Implementation: Preference Capture and Input Intelligence

This phase implements the `preference-service` and input parsing described in `phase_wise_architecture.md`.

## Implemented capabilities
- Validates required and optional preference fields.
- Normalizes:
  - location (city/locality canonicalization)
  - budget (`budget_amount` INR to range `0..budget_amount`)
  - cuisine aliases to canonical tokens
- Parses free text and optional fields into derived intent tags.
- Produces a normalized preference object for Phase 4 retrieval.

## Files
- `phase3/src/preference_service.py`
- `phase3/requirements.txt`

## Example usage (Python)
```python
from phase3.src.preference_service import PreferenceInput, normalize_preferences

payload = PreferenceInput(
    location="Indiranagar, Bangalore",
    budget_amount=1800,
    cuisine=["italian", "continental"],
    min_rating=4.0,
    free_text_notes="family-friendly with quick service",
)

normalized = normalize_preferences(payload)
print(normalized.model_dump())
```
