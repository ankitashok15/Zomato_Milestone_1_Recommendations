# Functional Requirements (Phase 1)

## 1. Product goal
Build an AI-powered restaurant recommendation service that accepts user preferences and returns ranked, explainable restaurant suggestions.

## 2. Scope in Phase 1
Phase 1 defines contracts and quality targets. It does not implement ingestion, APIs, or LLM calls yet.

## 3. Functional requirements

### FR-01 User preference capture contract
The system shall support the following user preference fields:
- `location` (city/locality text)
- `budget_amount` (integer INR: maximum acceptable cost for two people)
- `cuisine` (single or multiple cuisine preferences)
- `min_rating` (decimal, range `0.0` to `5.0`)
- `additional_preferences` (optional free text)

### FR-02 Catalog query intent
The system shall define a query contract capable of filtering restaurants by:
- location
- numeric budget (cost-for-two up to `budget_amount` INR)
- cuisine
- minimum rating

### FR-03 Recommendation output contract
The system shall define a recommendation result contract including:
- restaurant name
- cuisine
- rating
- estimated cost
- AI-generated explanation

### FR-04 Explainability requirement
Each recommendation result shall include a user-readable reason aligned with the provided preferences.

### FR-05 Ranking requirement
The system shall return recommendations in ranked order (`1..K`).

### FR-06 Data lineage requirement
The system shall track source dataset version and processing run metadata for traceability.

### FR-07 Feedback readiness
The system shall define feedback event contracts (click/like/not relevant) for future online evaluation.

## 4. Out-of-scope in Phase 1
- UI design implementation
- Data pipeline execution
- Database provisioning
- LLM integration
- Deployment and operations

## 5. Dependencies for next phases
- Approved domain model
- Approved request/response contracts
- Approved KPI and NFR targets
