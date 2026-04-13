from __future__ import annotations

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from phase6.src.recommendation_api import RecommendationRequest, recommendations


def _contains_expected_cuisine(item: dict, expected: str) -> bool:
    expected_lower = expected.lower()
    cuisines = item.get("cuisine", [])
    return any(expected_lower == str(c).lower() for c in cuisines)


def run_offline_eval() -> dict:
    benchmark_path = PROJECT_ROOT / "phase7" / "benchmarks" / "offline_queries.json"
    benchmarks = json.loads(benchmark_path.read_text(encoding="utf-8"))

    case_results = []
    hits = 0
    total = len(benchmarks)
    fallback_count = 0
    empty_count = 0

    for case in benchmarks:
        payload = RecommendationRequest(
            location=case["location"],
            budget_amount=case["budget_amount"],
            cuisine=case["cuisine"],
            min_rating=case["min_rating"],
            top_n_candidates=30,
            top_k_results=case.get("top_k_results", 5),
            include_debug=True,
        )
        response = recommendations(payload)
        top_recommendations = response.get("top_recommendations", [])
        if not top_recommendations:
            empty_count += 1
        hit = any(
            _contains_expected_cuisine(item, case["expected_cuisine"])
            for item in top_recommendations
        )
        if hit:
            hits += 1
        if response.get("debug", {}).get("used_fallback"):
            fallback_count += 1

        case_results.append(
            {
                "id": case["id"],
                "expected_cuisine": case["expected_cuisine"],
                "hit_at_k": hit,
                "result_count": len(top_recommendations),
                "used_fallback": response.get("debug", {}).get("used_fallback", False),
                "summary": response.get("summary", ""),
            }
        )

    precision_at_k = hits / total if total else 0.0
    fallback_rate = fallback_count / total if total else 0.0
    empty_response_rate = empty_count / total if total else 0.0

    report = {
        "total_cases": total,
        "precision_at_k_proxy": round(precision_at_k, 4),
        "fallback_rate": round(fallback_rate, 4),
        "empty_response_rate": round(empty_response_rate, 4),
        "cases": case_results,
    }
    reports_dir = PROJECT_ROOT / "phase7" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "latest_offline_eval.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


if __name__ == "__main__":
    report = run_offline_eval()
    print(json.dumps(report, indent=2))
