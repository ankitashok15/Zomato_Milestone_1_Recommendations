"""
Zomato AI recommender — Streamlit UI (same pipeline as FastAPI phase6).

Local:
  pip install -r requirements-streamlit.txt
  # Ensure phase2 processed CSVs exist under phase2/data/processed/
  streamlit run streamlit_app.py

Streamlit Community Cloud:
  Main file: streamlit_app.py
  Dependencies: repo-root requirements.txt (default) or requirements-streamlit.txt
  Secrets: GROQ_API_KEY (and optional GROQ_MODEL)
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import streamlit as st
from pydantic import BaseModel, Field, ValidationError

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - Streamlit Cloud should install python-dotenv

    def load_dotenv(*_args: Any, **_kwargs: Any) -> bool:
        return False

from phase3.src.preference_service import PreferenceInput, normalize_preferences
from phase4.src.retrieval_service import RetrievalService
from phase5.src.llm_orchestrator import GroqLLMOrchestrator
from phase8.src.ops import CircuitBreaker, MetricsCollector

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")


def _apply_streamlit_secrets() -> None:
    try:
        for key in ("GROQ_API_KEY", "GROQ_MODEL"):
            if key in st.secrets:
                os.environ[key] = str(st.secrets[key])
    except (AttributeError, FileNotFoundError, RuntimeError, TypeError):
        pass


class RecommendationRequest(PreferenceInput):
    top_n_candidates: int = Field(default=30, ge=1, le=50)
    top_k_results: int = Field(default=5, ge=1, le=10)
    include_debug: bool = Field(default=False)


class FeedbackPayload(BaseModel):
    request_id: str = Field(min_length=4)
    restaurant_id: str = Field(min_length=4)
    event_value: str | None = None


FEEDBACK_FILE = PROJECT_ROOT / "phase6" / "data" / "feedback_events.jsonl"


@st.cache_resource
def get_services() -> tuple[RetrievalService, GroqLLMOrchestrator, CircuitBreaker, MetricsCollector]:
    retrieval = RetrievalService(project_root=PROJECT_ROOT)
    llm = GroqLLMOrchestrator()
    circuit = CircuitBreaker(failure_threshold=3, recovery_timeout_seconds=60)
    metrics = MetricsCollector()
    return retrieval, llm, circuit, metrics


def run_recommendations(
    payload: RecommendationRequest,
    retrieval: RetrievalService,
    llm: GroqLLMOrchestrator,
    circuit_breaker: CircuitBreaker,
    metrics: MetricsCollector,
) -> dict[str, Any]:
    metrics.inc("recommendation_requests_total")
    normalized = normalize_preferences(payload)
    candidate_result = retrieval.retrieve_candidates(normalized, top_n=payload.top_n_candidates)

    if candidate_result.total_candidates == 0:
        return {
            "request_id": normalized.request_id,
            "top_recommendations": [],
            "summary": "No matching restaurants found for provided preferences.",
        }

    if not circuit_breaker.allow_request():
        metrics.inc("recommendation_fallback_responses")
        llm_result = llm.deterministic_fallback(
            candidates=candidate_result.candidates,
            top_k=payload.top_k_results,
        )
    else:
        try:
            llm_result = llm.generate_recommendations(
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
            llm_result = llm.deterministic_fallback(
                candidates=candidate_result.candidates,
                top_k=payload.top_k_results,
            )

    candidate_lookup = {c["restaurant_id"]: c for c in candidate_result.candidates}
    top_recommendations: list[dict[str, Any]] = []
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

    response: dict[str, Any] = {
        "request_id": normalized.request_id,
        "top_recommendations": sorted(top_recommendations, key=lambda x: x["rank"]),
        "summary": llm_result.summary,
    }
    if payload.include_debug:
        response["debug"] = {
            "used_fallback": llm_result.used_fallback,
            "total_candidates": candidate_result.total_candidates,
            "circuit_breaker": circuit_breaker.snapshot(),
        }
    metrics.inc("recommendation_requests_success")
    return response


def persist_feedback(event_type: str, payload: FeedbackPayload) -> None:
    FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "feedback_id": f"fb_{uuid4().hex[:12]}",
        "event_type": event_type,
        "request_id": payload.request_id,
        "restaurant_id": payload.restaurant_id,
        "event_value": payload.event_value,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    with FEEDBACK_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


def main() -> None:
    # Must be the first Streamlit command (accessing st.secrets before this breaks the app on Cloud).
    st.set_page_config(page_title="Zomato AI Recommender", layout="wide")
    _apply_streamlit_secrets()

    st.title("Zomato AI Recommender")
    st.caption("Streamlit app — same retrieval + LLM path as `phase6` FastAPI.")

    try:
        retrieval, llm, circuit, metrics = get_services()
    except FileNotFoundError as e:
        st.error(f"Data not found: {e}")
        st.info("Run **Phase 2 ingestion** locally: `python phase2/src/ingest_zomato.py` then redeploy or refresh data.")
        st.stop()
    except Exception as e:
        st.error("Could not load restaurant catalog or services.")
        st.exception(e)
        st.stop()

    localities = retrieval.list_localities()
    cuisines = retrieval.list_cuisines()
    if not localities or not cuisines:
        st.error("Localities or cuisines list is empty. Check processed CSVs under `phase2/data/processed/`.")
        st.stop()

    if not os.getenv("GROQ_API_KEY"):
        st.warning("**GROQ_API_KEY** is not set. Add it to `.env` locally or Streamlit **Secrets** for LLM ranking.")

    col1, col2 = st.columns(2)
    with col1:
        locality = st.selectbox("Locality", options=[""] + localities, format_func=lambda x: x or "Select…")
    with col2:
        budget = st.number_input("Max budget (INR, cost for two)", min_value=50, max_value=100_000, value=1200, step=50)

    cuisine_filter = st.text_input("Filter cuisines (optional)", "")
    filtered = [c for c in cuisines if not cuisine_filter.strip() or cuisine_filter.lower() in c.lower()]
    if not filtered:
        st.warning("No cuisines match that filter — showing all cuisines for this control.")
        filtered = list(cuisines)
    default_pick = [c for c in filtered if c == "North Indian"] or ([filtered[0]] if filtered else [])
    selected_cuisines = st.multiselect("Cuisines", options=filtered, default=default_pick)

    c3, c4, c5 = st.columns(3)
    with c3:
        min_rating = st.number_input("Minimum rating", min_value=0.0, max_value=5.0, value=3.8, step=0.1)
    with c4:
        top_k = st.number_input("Top K results", min_value=1, max_value=10, value=5)
    with c5:
        top_n = st.number_input("Candidate pool (N)", min_value=10, max_value=50, value=30)

    party = st.text_input("Party type (optional)", "")
    service = st.text_input("Service expectation (optional)", "")
    notes = st.text_area("Additional preferences (optional)", "")
    include_debug = st.checkbox("Include debug block", value=False)

    if st.button("Get recommendations", type="primary"):
        if not locality:
            st.error("Please select a locality.")
        elif not selected_cuisines:
            st.error("Select at least one cuisine.")
        else:
            try:
                req = RecommendationRequest(
                    location=locality,
                    budget_amount=int(budget),
                    cuisine=selected_cuisines,
                    min_rating=float(min_rating),
                    party_type=party.strip() or None,
                    service_expectation=service.strip() or None,
                    free_text_notes=notes.strip() or None,
                    top_k_results=int(top_k),
                    top_n_candidates=int(top_n),
                    include_debug=include_debug,
                )
            except ValidationError as err:
                st.error(err)
            else:
                with st.spinner("Ranking restaurants…"):
                    try:
                        data = run_recommendations(req, retrieval, llm, circuit, metrics)
                    except Exception as e:
                        st.exception(e)
                    else:
                        st.session_state["last_result"] = data
                        st.session_state["metrics_snapshot"] = metrics.snapshot()
                        st.success("Recommendations updated below.")

    result = st.session_state.get("last_result")
    if result:
        st.subheader("Results")
        st.write(result.get("summary") or "")
        items = result.get("top_recommendations") or []
        if not items:
            st.info("No recommendations returned.")
        rid = result.get("request_id", "")
        for item in items:
            with st.expander(f"#{item['rank']} — {item['restaurant_name']}", expanded=item["rank"] <= 2):
                st.write(
                    f"**Rating:** {item['rating']} | **Cost:** {item['estimated_cost']} {item.get('currency', 'INR')}"
                )
                st.caption(", ".join(item.get("cuisine") or []))
                st.write(item.get("ai_explanation", ""))
                if item.get("cautions"):
                    st.caption(item["cautions"])
                b1, b2, b3 = st.columns(3)
                for col, ev, label in (
                    (b1, "click", "Click"),
                    (b2, "like", "Like"),
                    (b3, "not_relevant", "Not relevant"),
                ):
                    if col.button(label, key=f"{rid}-{item['restaurant_id']}-{ev}"):
                        try:
                            persist_feedback(
                                ev,
                                FeedbackPayload(
                                    request_id=rid,
                                    restaurant_id=item["restaurant_id"],
                                    event_value=f"streamlit-{ev}",
                                ),
                            )
                            st.toast(f"Recorded: {label}")
                        except OSError as e:
                            st.warning(f"Could not save feedback: {e}")

        if result.get("debug"):
            with st.expander("Debug"):
                st.json(result["debug"])

    snap = st.session_state.get("metrics_snapshot")
    if snap:
        with st.expander("Session metrics (counters)"):
            st.json(snap)


main()
