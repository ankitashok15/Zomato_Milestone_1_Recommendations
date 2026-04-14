from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import BaseModel, Field, ValidationError, field_validator

from phase3.src.preference_service import NormalizedPreference


class RecommendationItem(BaseModel):
    restaurant_id: str
    rank: int = Field(ge=1)
    fit_score: int = Field(ge=0, le=100)
    explanation: str = Field(min_length=10)
    cautions: str | None = None


class LLMOutput(BaseModel):
    summary: str = Field(min_length=5)
    recommendations: list[RecommendationItem]

    @field_validator("recommendations")
    @classmethod
    def validate_non_empty(cls, value: list[RecommendationItem]) -> list[RecommendationItem]:
        if not value:
            raise ValueError("recommendations cannot be empty")
        return value


@dataclass
class OrchestrationResult:
    summary: str
    recommendations: list[dict[str, Any]]
    used_fallback: bool


class GroqLLMOrchestrator:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_retries: int = 1,
        timeout_seconds: float = 12.0,
    ) -> None:
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.model = model or os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.cache_ttl_seconds = max(0.0, float(os.getenv("LLM_CACHE_TTL_SECONDS", "30")))
        self.cache: dict[str, tuple[float, OrchestrationResult]] = {}

    def _cache_key(
        self,
        normalized_pref: NormalizedPreference,
        candidates: list[dict[str, Any]],
        top_k: int,
    ) -> str:
        candidate_part = ",".join(c["restaurant_id"] for c in candidates[:50])
        pref_part = "|".join(
            [
                normalized_pref.normalized_location.city.lower(),
                (normalized_pref.normalized_location.locality or "").lower(),
                str(normalized_pref.budget_amount),
                ",".join(sorted([c.lower() for c in normalized_pref.canonical_cuisines])),
                str(normalized_pref.min_rating),
                ",".join(sorted(normalized_pref.derived_tags)),
                str(top_k),
            ]
        )
        return f"{pref_part}|{candidate_part}"

    def _extract_json_payload(self, text: str) -> dict[str, Any]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start >= 0 and end > start:
                return json.loads(cleaned[start : end + 1])
            raise

    def _cache_get(self, key: str) -> OrchestrationResult | None:
        cached = self.cache.get(key)
        if not cached:
            return None
        created_at, value = cached
        if self.cache_ttl_seconds and (time.monotonic() - created_at > self.cache_ttl_seconds):
            self.cache.pop(key, None)
            return None
        return value

    def _cache_set(self, key: str, value: OrchestrationResult) -> None:
        if self.cache_ttl_seconds <= 0:
            return
        self.cache[key] = (time.monotonic(), value)

    def _build_prompt(
        self,
        normalized_pref: NormalizedPreference,
        candidates: list[dict[str, Any]],
        top_k: int,
    ) -> list[dict[str, str]]:
        compact_candidates = []
        for candidate in candidates[:50]:
            compact_candidates.append(
                {
                    "restaurant_id": candidate["restaurant_id"],
                    "name": candidate["name"],
                    "cuisines": candidate.get("cuisines", []),
                    "rating": candidate["rating"],
                    "avg_cost_for_two": candidate["avg_cost_for_two"],
                    "price_band": candidate["price_band"],
                    "city": candidate["city"],
                    "locality": candidate.get("locality"),
                    "deterministic_score": candidate.get("scoring", {}).get("score"),
                }
            )

        system_prompt = (
            "You are a restaurant recommendation ranker. "
            "Use ONLY the candidate restaurants provided by the user. "
            "Every candidate already matches the user's location, budget, rating floor, and at least one "
            "requested cuisine — rank them by how well they fit the full preference profile (cuisines, notes). "
            "Return STRICT JSON only, no markdown, no prose outside JSON."
        )

        user_prompt = {
            "task": "Rank restaurants and explain why they fit user preferences.",
            "constraints": {
                "top_k": top_k,
                "allowed_restaurant_ids": [c["restaurant_id"] for c in compact_candidates],
                "output_schema": {
                    "summary": "string",
                    "recommendations": [
                        {
                            "restaurant_id": "string",
                            "rank": "integer starting at 1",
                            "fit_score": "integer 0-100",
                            "explanation": "string",
                            "cautions": "string or null",
                        }
                    ],
                },
            },
            "user_preference": normalized_pref.model_dump(),
            "candidates": compact_candidates,
        }

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_prompt)},
        ]

    def _call_groq(self, messages: list[dict[str, str]]) -> str:
        if not self.api_key:
            raise RuntimeError("GROQ_API_KEY is not configured.")

        url = "https://api.groq.com/openai/v1/chat/completions"
        payload = {
            "model": self.model,
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
            "messages": messages,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            body = response.json()
            return body["choices"][0]["message"]["content"]

    def _validate_llm_output(
        self, raw_json: dict[str, Any], candidate_ids: set[str], top_k: int
    ) -> LLMOutput:
        parsed = LLMOutput.model_validate(raw_json)

        filtered: list[RecommendationItem] = []
        seen: set[str] = set()
        for item in sorted(parsed.recommendations, key=lambda x: x.rank):
            if item.restaurant_id not in candidate_ids:
                raise ValueError(f"Unknown restaurant_id from LLM: {item.restaurant_id}")
            if item.restaurant_id in seen:
                continue
            seen.add(item.restaurant_id)
            filtered.append(item)
            if len(filtered) >= top_k:
                break

        if not filtered:
            raise ValueError("LLM output did not contain valid candidate restaurant IDs.")

        # Re-rank sequentially to enforce strict rank order.
        repaired = []
        for idx, item in enumerate(filtered, start=1):
            repaired.append(
                RecommendationItem(
                    restaurant_id=item.restaurant_id,
                    rank=idx,
                    fit_score=item.fit_score,
                    explanation=item.explanation,
                    cautions=item.cautions,
                )
            )
        return LLMOutput(summary=parsed.summary, recommendations=repaired)

    def _fallback(
        self,
        candidates: list[dict[str, Any]],
        top_k: int,
    ) -> OrchestrationResult:
        fallback_items = []
        for idx, candidate in enumerate(candidates[:top_k], start=1):
            score = candidate.get("scoring", {})
            explanation = (
                f"Strong deterministic fit: rating {candidate['rating']}, "
                f"budget aligned, and cuisine relevance score {score.get('cuisine_match', 0)}."
            )
            fallback_items.append(
                {
                    "restaurant_id": candidate["restaurant_id"],
                    "rank": idx,
                    "fit_score": int(round(float(score.get("score", 0)) * 100)),
                    "explanation": explanation,
                    "cautions": "Generated via deterministic fallback (LLM unavailable).",
                }
            )
        return OrchestrationResult(
            summary="Fallback recommendations generated from deterministic ranking.",
            recommendations=fallback_items,
            used_fallback=True,
        )

    def deterministic_fallback(
        self, candidates: list[dict[str, Any]], top_k: int = 5
    ) -> OrchestrationResult:
        top_k = max(1, min(top_k, 10))
        return self._fallback(candidates, top_k)

    def generate_recommendations(
        self,
        normalized_pref: NormalizedPreference,
        candidates: list[dict[str, Any]],
        top_k: int = 5,
    ) -> OrchestrationResult:
        top_k = max(1, min(top_k, 10))
        if not candidates:
            return OrchestrationResult(
                summary="No candidates available for the provided preferences.",
                recommendations=[],
                used_fallback=True,
            )

        cache_key = self._cache_key(normalized_pref, candidates, top_k)
        cached = self._cache_get(cache_key)
        if cached:
            return cached

        candidate_ids = {c["restaurant_id"] for c in candidates}
        candidate_lookup = {c["restaurant_id"]: c for c in candidates}
        messages = self._build_prompt(normalized_pref, candidates, top_k)

        for _ in range(self.max_retries + 1):
            try:
                raw_text = self._call_groq(messages)
                raw_json = self._extract_json_payload(raw_text)
                validated = self._validate_llm_output(raw_json, candidate_ids, top_k)
                combined_rank: list[tuple[float, RecommendationItem]] = []
                for item in validated.recommendations:
                    deterministic_score = float(
                        candidate_lookup.get(item.restaurant_id, {})
                        .get("scoring", {})
                        .get("score", 0.0)
                    )
                    llm_score = float(item.fit_score) / 100.0
                    final_score = (0.75 * deterministic_score) + (0.25 * llm_score)
                    combined_rank.append((final_score, item))
                reranked_items = [entry[1] for entry in sorted(combined_rank, key=lambda x: x[0], reverse=True)]
                repaired_recommendations: list[dict[str, Any]] = []
                for idx, item in enumerate(reranked_items[:top_k], start=1):
                    repaired_recommendations.append(
                        {
                            "restaurant_id": item.restaurant_id,
                            "rank": idx,
                            "fit_score": item.fit_score,
                            "explanation": item.explanation,
                            "cautions": item.cautions,
                        }
                    )
                result = OrchestrationResult(
                    summary=validated.summary,
                    recommendations=repaired_recommendations,
                    used_fallback=False,
                )
                self._cache_set(cache_key, result)
                return result
            except (httpx.HTTPError, json.JSONDecodeError, ValidationError, ValueError, RuntimeError):
                continue

        result = self._fallback(candidates, top_k=top_k)
        self._cache_set(cache_key, result)
        return result
