from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

from fastapi import HTTPException

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from phase3.src.preference_service import PreferenceInput, normalize_preferences
from phase4.src.retrieval_service import RetrievalService
from phase5.src.llm_orchestrator import GroqLLMOrchestrator
from phase6.src.recommendation_api import (
    RecommendationRequest,
    recommendations,
    verify_api_key,
)


@dataclass
class TestResult:
    name: str
    passed: bool
    details: str


def test_llm_orchestrator_live_connection() -> TestResult:
    retrieval_service = RetrievalService(project_root=PROJECT_ROOT)
    pref = PreferenceInput(
        location="Bangalore",
        budget_amount=1800,
        cuisine=["North Indian"],
        min_rating=3.8,
    )
    normalized = normalize_preferences(pref)
    candidates = retrieval_service.retrieve_candidates(normalized, top_n=20).candidates
    orchestrator = GroqLLMOrchestrator(max_retries=1)
    result = orchestrator.generate_recommendations(
        normalized_pref=normalized,
        candidates=candidates,
        top_k=3,
    )

    if len(result.recommendations) >= 1 and result.used_fallback is False:
        return TestResult(
            name="LLM live connection returns structured output",
            passed=True,
            details=f"Received {len(result.recommendations)} LLM-ranked recommendations.",
        )
    return TestResult(
        name="LLM live connection returns structured output",
        passed=False,
        details="LLM result empty or fallback was used (possible key/network issue).",
    )


def test_recommendations_api_path() -> TestResult:
    payload = RecommendationRequest(
        location="Bangalore",
        budget_amount=1800,
        cuisine=["North Indian"],
        min_rating=3.8,
        top_n_candidates=20,
        top_k_results=3,
        include_debug=True,
    )
    response = recommendations(payload)
    ok = (
        response.get("request_id")
        and isinstance(response.get("top_recommendations"), list)
        and len(response["top_recommendations"]) >= 1
        and "summary" in response
    )
    if ok:
        return TestResult(
            name="Recommendations API business flow",
            passed=True,
            details=f"Returned {len(response['top_recommendations'])} recommendations.",
        )
    return TestResult(
        name="Recommendations API business flow",
        passed=False,
        details="Unexpected response shape from recommendations flow.",
    )


def test_api_key_enforcement() -> TestResult:
    try:
        verify_api_key("invalid_key")
        return TestResult(
            name="API key enforcement",
            passed=False,
            details="verify_api_key accepted an invalid key.",
        )
    except HTTPException as exc:
        if exc.status_code == 401:
            return TestResult(
                name="API key enforcement",
                passed=True,
                details="Invalid key correctly rejected with 401.",
            )
        return TestResult(
            name="API key enforcement",
            passed=False,
            details=f"Expected 401, got {exc.status_code}.",
        )


def test_llm_hallucination_guardrail_fallback() -> TestResult:
    class FakeBadLLM(GroqLLMOrchestrator):
        def _call_groq(self, messages):  # type: ignore[override]
            return '{"summary":"x","recommendations":[{"restaurant_id":"res_not_in_candidates","rank":1,"fit_score":90,"explanation":"bad id","cautions":null}]}'

    retrieval_service = RetrievalService(project_root=PROJECT_ROOT)
    pref = PreferenceInput(
        location="Bangalore",
        budget_amount=1800,
        cuisine=["North Indian"],
        min_rating=3.8,
    )
    normalized = normalize_preferences(pref)
    candidates = retrieval_service.retrieve_candidates(normalized, top_n=10).candidates
    orchestrator = FakeBadLLM(max_retries=0)
    result = orchestrator.generate_recommendations(
        normalized_pref=normalized,
        candidates=candidates,
        top_k=3,
    )
    if result.used_fallback and len(result.recommendations) >= 1:
        return TestResult(
            name="LLM hallucination guardrail and fallback",
            passed=True,
            details="Unknown restaurant_id was blocked; fallback executed.",
        )
    return TestResult(
        name="LLM hallucination guardrail and fallback",
        passed=False,
        details="Fallback did not trigger for invalid LLM restaurant_id.",
    )


def main() -> None:
    tests = [
        test_llm_orchestrator_live_connection,
        test_recommendations_api_path,
        test_api_key_enforcement,
        test_llm_hallucination_guardrail_fallback,
    ]
    results: list[TestResult] = []
    for test_fn in tests:
        try:
            results.append(test_fn())
        except Exception as exc:
            results.append(
                TestResult(
                    name=test_fn.__name__,
                    passed=False,
                    details=f"Unhandled exception: {exc}",
                )
            )

    passed = sum(1 for result in results if result.passed)
    total = len(results)
    print(f"Executed {total} tests. Passed: {passed}. Failed: {total - passed}.")
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"[{status}] {result.name} -> {result.details}")

    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
