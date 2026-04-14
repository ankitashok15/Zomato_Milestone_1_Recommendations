from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from phase3.src.preference_service import PreferenceInput, normalize_preferences
from phase4.src.retrieval_service import RetrievalService
from phase5.src.llm_orchestrator import GroqLLMOrchestrator
from phase8.src.ops import CircuitBreaker, MetricsCollector, RateLimiter

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

app = FastAPI(title="Zomato Recommendation Service", version="1.0.0")
retrieval_service = RetrievalService(project_root=Path(__file__).resolve().parents[2])
llm_orchestrator = GroqLLMOrchestrator()

RECOMMENDATION_API_KEY = os.getenv("RECOMMENDATION_API_KEY", "")
FEEDBACK_FILE = Path(__file__).resolve().parents[1] / "data" / "feedback_events.jsonl"
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
FRONTEND_INDEX = FRONTEND_DIR / "index.html"
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "40"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
CORS_ALLOW_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOW_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,https://zomato-milestone-1-recommendations-lemon.vercel.app",
    ).split(",")
    if origin.strip()
]

rate_limiter = RateLimiter(
    max_requests=RATE_LIMIT_MAX_REQUESTS,
    window_seconds=RATE_LIMIT_WINDOW_SECONDS,
)
circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout_seconds=60)
metrics = MetricsCollector()

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


class RecommendationRequest(PreferenceInput):
    top_n_candidates: int = Field(default=30, ge=1, le=50)
    top_k_results: int = Field(default=5, ge=1, le=10)
    include_debug: bool = Field(default=False)


class FeedbackRequest(BaseModel):
    request_id: str = Field(min_length=4)
    restaurant_id: str = Field(min_length=4)
    event_value: str | None = None


def verify_api_key(x_api_key: str = Header(default="", alias="X-API-Key")) -> None:
    if not RECOMMENDATION_API_KEY:
        metrics.inc("auth_config_errors")
        raise HTTPException(
            status_code=500,
            detail="RECOMMENDATION_API_KEY is not configured in .env",
        )
    if x_api_key != RECOMMENDATION_API_KEY:
        metrics.inc("auth_failures")
        raise HTTPException(status_code=401, detail="Invalid API key")
    if not rate_limiter.is_allowed(x_api_key):
        metrics.inc("rate_limit_hits")
        raise HTTPException(status_code=429, detail="Rate limit exceeded")


def _persist_feedback(event_type: str, payload: FeedbackRequest) -> dict:
    FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "feedback_id": f"fb_{uuid4().hex[:12]}",
        "event_type": event_type,
        "request_id": payload.request_id,
        "restaurant_id": payload.restaurant_id,
        "event_value": payload.event_value,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    with FEEDBACK_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(event) + "\n")
    return event


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/ui")


@app.get("/ui")
def ui() -> FileResponse:
    if not FRONTEND_INDEX.exists():
        raise HTTPException(status_code=404, detail="Frontend UI file not found.")
    return FileResponse(FRONTEND_INDEX)


@app.get("/health/detailed")
def health_detailed() -> dict:
    return {
        "status": "ok",
        "circuit_breaker": circuit_breaker.snapshot(),
        "metrics": metrics.snapshot(),
    }


@app.get("/internal/metrics", dependencies=[Depends(verify_api_key)])
def internal_metrics() -> dict:
    return metrics.snapshot()


@app.get("/localities", dependencies=[Depends(verify_api_key)])
def api_localities() -> dict:
    return {"localities": retrieval_service.list_localities()}


@app.get("/cuisines", dependencies=[Depends(verify_api_key)])
def api_cuisines() -> dict:
    return {"cuisines": retrieval_service.list_cuisines()}


@app.get("/ui-api/localities")
def ui_localities() -> dict:
    return {"localities": retrieval_service.list_localities()}


@app.get("/ui-api/cuisines")
def ui_cuisines() -> dict:
    return {"cuisines": retrieval_service.list_cuisines()}


@app.post("/recommendations", dependencies=[Depends(verify_api_key)])
def recommendations(payload: RecommendationRequest) -> dict:
    metrics.inc("recommendation_requests_total")
    normalized = normalize_preferences(payload)
    candidate_result = retrieval_service.retrieve_candidates(
        normalized, top_n=payload.top_n_candidates
    )

    if candidate_result.total_candidates == 0:
        return {
            "request_id": normalized.request_id,
            "top_recommendations": [],
            "summary": "No matching restaurants found for provided preferences.",
        }

    if not circuit_breaker.allow_request():
        metrics.inc("recommendation_fallback_responses")
        llm_result = llm_orchestrator.deterministic_fallback(
            candidates=candidate_result.candidates,
            top_k=payload.top_k_results,
        )
    else:
        try:
            llm_result = llm_orchestrator.generate_recommendations(
                normalized_pref=normalized,
                candidates=candidate_result.candidates,
                top_k=payload.top_k_results,
            )
            circuit_breaker.on_success()
            if llm_result.used_fallback:
                metrics.inc("recommendation_fallback_responses")
        except Exception:
            circuit_breaker.on_failure()
            metrics.inc("recommendation_fallback_responses")
            llm_result = llm_orchestrator.deterministic_fallback(
                candidates=candidate_result.candidates,
                top_k=payload.top_k_results,
            )

    candidate_lookup = {c["restaurant_id"]: c for c in candidate_result.candidates}
    top_recommendations = []
    for item in llm_result.recommendations:
        candidate = candidate_lookup.get(item["restaurant_id"])
        if not candidate:
            continue
        top_recommendations.append(
            {
                "rank": item["rank"],
                "restaurant_id": item["restaurant_id"],
                "restaurant_name": candidate["name"],
                "cuisine": candidate.get("cuisines", []),
                "rating": candidate["rating"],
                "estimated_cost": candidate["avg_cost_for_two"],
                "currency": "INR",
                "ai_explanation": item["explanation"],
                "cautions": item.get("cautions"),
            }
        )

    response = {
        "request_id": normalized.request_id,
        "top_recommendations": sorted(top_recommendations, key=lambda x: x["rank"]),
        "summary": llm_result.summary,
    }
    if payload.include_debug:
        response["debug"] = {
            "used_fallback": llm_result.used_fallback,
            "total_candidates": candidate_result.total_candidates,
            "normalized_preference": normalized.model_dump(),
            "circuit_breaker": circuit_breaker.snapshot(),
        }
    metrics.inc("recommendation_requests_success")
    return response


@app.post("/ui-api/recommendations")
def ui_recommendations(payload: RecommendationRequest) -> dict:
    # UI proxy endpoint: server-side app already has .env context,
    # so browser users do not need to provide API key manually.
    return recommendations(payload)


@app.post("/feedback/click", dependencies=[Depends(verify_api_key)])
def feedback_click(payload: FeedbackRequest) -> dict:
    metrics.inc("feedback_events_total")
    return _persist_feedback("click", payload)


@app.post("/feedback/like", dependencies=[Depends(verify_api_key)])
def feedback_like(payload: FeedbackRequest) -> dict:
    metrics.inc("feedback_events_total")
    return _persist_feedback("like", payload)


@app.post("/feedback/not_relevant", dependencies=[Depends(verify_api_key)])
def feedback_not_relevant(payload: FeedbackRequest) -> dict:
    metrics.inc("feedback_events_total")
    return _persist_feedback("not_relevant", payload)


@app.post("/ui-api/feedback/click")
def ui_feedback_click(payload: FeedbackRequest) -> dict:
    return feedback_click(payload)


@app.post("/ui-api/feedback/like")
def ui_feedback_like(payload: FeedbackRequest) -> dict:
    return feedback_like(payload)


@app.post("/ui-api/feedback/not_relevant")
def ui_feedback_not_relevant(payload: FeedbackRequest) -> dict:
    return feedback_not_relevant(payload)


@app.get("/ui-api/metrics")
def ui_metrics() -> dict[str, int]:
    return metrics.snapshot()


@app.get("/top-restaurants", dependencies=[Depends(verify_api_key)])
def top_restaurants(locality: str, limit: int = 5) -> dict:
    items = retrieval_service.top_restaurants_by_locality(locality=locality, limit=limit)
    return {"locality": locality, "top_restaurants": items}


@app.get("/ui-api/top-restaurants")
def ui_top_restaurants(locality: str, limit: int = 5) -> dict:
    return top_restaurants(locality=locality, limit=limit)
