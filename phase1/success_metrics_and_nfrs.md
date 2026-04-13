# Success Metrics and Non-Functional Requirements (Phase 1)

## 1. Quality KPIs (initial baseline targets)

### Recommendation relevance
- `Precision@5 >= 0.70` on curated offline benchmark set.
- `NDCG@5 >= 0.75` on same benchmark.

### Explainability quality
- `>= 90%` of sampled responses include preference-grounded explanations.
- `>= 95%` of explanations are free of unsupported restaurant claims.

### Product effectiveness (online, post-launch)
- Recommendation click-through rate (CTR) baseline established in first release.
- `Like / (Like + Not Relevant)` tracked by city and cuisine segment.

## 2. Performance targets
- P95 latency (cached recommendation): `<= 2.5s`
- P95 latency (uncached recommendation): `<= 6.0s`
- Retrieval-only stage P95: `<= 300ms` (warm path)

## 3. Reliability targets
- API availability target: `99.5%` monthly.
- Graceful fallback to deterministic ranking if LLM fails.
- No single point of failure in request handling path.

## 4. Cost targets
- Define max token budget per request (to be finalized in Phase 5).
- Track cost per 1,000 requests by city and traffic segment.
- Cache hit ratio target: `>= 35%` for repeated preference patterns.

## 5. Security and compliance targets
- No plaintext secrets in source code.
- Prompt and logs must avoid unnecessary PII.
- Request tracing enabled with `request_id` across services.

## 6. Observability requirements
- Mandatory metrics:
  - request count, latency, error rates
  - LLM usage and token cost
  - schema validation failures
  - cache hit/miss ratio
- Mandatory logs:
  - input validation outcomes
  - retrieval candidate counts
  - fallback activation reasons

## 7. Phase 1 acceptance conditions
- KPI definitions approved by product and engineering.
- NFR targets documented and feasible for planned architecture.
