# Phase 7 Implementation: Evaluation Framework and Continuous Improvement (Backend)

This phase adds offline/continuous evaluation utilities for the backend recommendation service.

## Implemented artifacts
- Benchmark query set (`phase7/benchmarks/offline_queries.json`)
- Offline evaluator (`phase7/src/evaluate_backend.py`) with:
  - Precision@K (proxy)
  - Fallback rate
  - Empty-response rate
  - Case-by-case outputs
- Experiment utility (`phase7/src/experiment_router.py`) for deterministic A/B assignment.

## Run evaluation
```powershell
python phase7/src/evaluate_backend.py
```

The evaluator writes report JSON to:
- `phase7/reports/latest_offline_eval.json`
