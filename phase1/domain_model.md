# Domain Model (Phase 1)

## 1. Core entities

### Restaurant
- `restaurant_id` (string, immutable identifier)
- `name` (string)
- `city` (string)
- `locality` (string, optional)
- `latitude` (number, optional)
- `longitude` (number, optional)
- `avg_cost_for_two` (number)
- `currency` (string, default `INR`)
- `price_band` (enum: `low`, `medium`, `high`)
- `rating` (number, `0.0..5.0`)
- `votes` (integer, optional)
- `is_active` (boolean)
- `updated_at` (datetime)

### Cuisine
- `cuisine_id` (string)
- `name` (string, canonical)
- `aliases` (string[], optional)

### UserPreference
- `preference_id` (string)
- `location` (string)
- `budget_amount` (integer INR: max cost for two)
- `cuisines` (string[])
- `min_rating` (number, `0.0..5.0`)
- `additional_preferences` (string, optional)
- `created_at` (datetime)

### RecommendationResult
- `request_id` (string)
- `rank` (integer)
- `restaurant_id` (string)
- `fit_score` (number, optional in early phases)
- `explanation` (string)
- `generated_at` (datetime)

### FeedbackEvent
- `feedback_id` (string)
- `request_id` (string)
- `restaurant_id` (string)
- `event_type` (enum: `click`, `like`, `not_relevant`)
- `event_value` (string, optional)
- `created_at` (datetime)

### DatasetRun
- `run_id` (string)
- `source_name` (string)
- `source_version` (string)
- `records_total` (integer)
- `records_loaded` (integer)
- `quality_report` (string/json)
- `created_at` (datetime)

## 2. Entity relationships
- A `Restaurant` has many `Cuisine` values (many-to-many).
- A `UserPreference` produces one recommendation request and many `RecommendationResult` items.
- A `RecommendationResult` references exactly one `Restaurant`.
- A `FeedbackEvent` references one recommendation request and one restaurant.
- A `DatasetRun` is linked to many ingested restaurants through lineage metadata.

## 3. Logical ER overview
- `restaurants` 1..* <-> *..1 `restaurant_cuisines`
- `recommendation_requests` 1..* -> `recommendation_results`
- `recommendation_results` *..1 -> `restaurants`
- `feedback_events` *..1 -> `recommendation_requests`
- `feedback_events` *..1 -> `restaurants`

## 4. Domain constraints
- `rating` must be in range `0.0..5.0`.
- `price_band` is derived from normalized cost policy.
- `rank` values are unique per `request_id`.
- `restaurant_id` in outputs must exist in catalog.
