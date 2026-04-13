from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from phase3.src.preference_service import (
    NormalizedPreference,
    PreferenceInput,
    normalize_preferences,
)
from phase4.src.retrieval_service import RetrievalService

app = FastAPI(title="Zomato Recommendation - Phase3/4 API", version="1.0.0")
retrieval_service = RetrievalService(project_root=Path(__file__).resolve().parents[2])


class CandidateRequest(BaseModel):
    normalized_preference: NormalizedPreference
    top_n: int = Field(default=30, ge=1, le=50)


class NormalizeAndCandidatesRequest(BaseModel):
    preference: PreferenceInput
    top_n: int = Field(default=30, ge=1, le=50)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/phase3/normalize")
def phase3_normalize(payload: PreferenceInput) -> dict:
    try:
        normalized = normalize_preferences(payload)
        return normalized.model_dump()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/phase4/candidates")
def phase4_candidates(payload: CandidateRequest) -> dict:
    try:
        result = retrieval_service.retrieve_candidates(
            pref=payload.normalized_preference, top_n=payload.top_n
        )
        return {
            "request_id": result.request_id,
            "total_candidates": result.total_candidates,
            "top_n": result.top_n,
            "candidates": result.candidates,
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/phase4/normalize-and-candidates")
def phase4_normalize_and_candidates(payload: NormalizeAndCandidatesRequest) -> dict:
    try:
        normalized = normalize_preferences(payload.preference)
        result = retrieval_service.retrieve_candidates(pref=normalized, top_n=payload.top_n)
        return {
            "normalized_preference": normalized.model_dump(),
            "total_candidates": result.total_candidates,
            "top_n": result.top_n,
            "candidates": result.candidates,
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
