# Phase 5 Implementation: LLM Orchestration and Explainable Recommendation

This phase implements Groq-based LLM orchestration with strict output validation and fallback behavior.

## Implemented capabilities
- Uses Groq Chat Completions API for reranking and explanations.
- Prompt template includes:
  - normalized user preference
  - candidate restaurants
  - strict JSON response schema instructions
- Output schema validation with retries.
- Hallucination guard:
  - rejects restaurant IDs not present in provided candidates
- Fallback policy:
  - if LLM fails validation/retries, returns deterministic top-K with template explanations
- Recommendation cache:
  - caches repeated normalized requests + candidate set combinations

## Files
- `phase5/src/llm_orchestrator.py`
- `phase5/requirements.txt`

## Required environment variables
- `GROQ_API_KEY`
- `GROQ_MODEL` (default used if not provided in constructor)
