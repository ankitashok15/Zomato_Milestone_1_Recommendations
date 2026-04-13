from __future__ import annotations

import re
from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

CITY_ALIASES = {
    "bangalore": "Bengaluru",
    "bengaluru": "Bengaluru",
    "new delhi": "Delhi",
    "delhi ncr": "Delhi",
    "bombay": "Mumbai",
}

CUISINE_ALIASES = {
    "north indian": "North Indian",
    "south indian": "South Indian",
    "chinese": "Chinese",
    "italian": "Italian",
    "continental": "Continental",
    "fast food": "Fast Food",
    "street food": "Street Food",
    "mughlai": "Mughlai",
    "biryani": "Biryani",
    "pizza": "Pizza",
    "burger": "Burger",
    "desserts": "Desserts",
}

TAG_KEYWORDS = {
    "family-friendly": ["family", "kids", "children", "family-friendly"],
    "quick-service": ["quick", "fast service", "quick service", "speedy"],
    "romantic": ["romantic", "date", "couple"],
    "vegan-options": ["vegan", "plant-based"],
    "vegetarian-options": ["vegetarian", "veg"],
    "outdoor-seating": ["outdoor", "rooftop", "open air"],
}


class PreferenceInput(BaseModel):
    location: str = Field(min_length=2, description="City or locality,city input")
    budget_amount: int = Field(
        ge=50,
        le=100_000,
        description="Max acceptable cost for two people (INR)",
    )
    cuisine: str | list[str]
    min_rating: float = Field(ge=0.0, le=5.0)
    party_type: str | None = None
    service_expectation: str | None = None
    dietary_preference: str | None = None
    free_text_notes: str | None = None

    @field_validator("location")
    @classmethod
    def validate_location(cls, value: str) -> str:
        normalized = " ".join(value.split()).strip()
        if not normalized:
            raise ValueError("location cannot be empty")
        return normalized

    @field_validator("cuisine")
    @classmethod
    def validate_cuisine(cls, value: str | list[str]) -> str | list[str]:
        if isinstance(value, str):
            cleaned = value.strip()
            if not cleaned:
                raise ValueError("cuisine cannot be empty")
            return cleaned
        if not value:
            raise ValueError("cuisine list cannot be empty")
        cleaned_list = [item.strip() for item in value if item and item.strip()]
        if not cleaned_list:
            raise ValueError("cuisine list cannot be empty")
        return cleaned_list


class NormalizedLocation(BaseModel):
    city: str
    locality: str | None = None


class BudgetRange(BaseModel):
    min_cost_for_two: int
    max_cost_for_two: int
    currency: str = "INR"


class NormalizedPreference(BaseModel):
    request_id: str
    normalized_location: NormalizedLocation
    budget_amount: int
    budget_range: BudgetRange
    canonical_cuisines: list[str]
    min_rating: float
    party_type: str | None = None
    service_expectation: str | None = None
    dietary_preference: str | None = None
    derived_tags: list[str]
    created_at_utc: str


def _normalize_city(city_candidate: str) -> str:
    token = " ".join(city_candidate.split()).strip().lower()
    if token in CITY_ALIASES:
        return CITY_ALIASES[token]
    return city_candidate.strip().title()


def _split_location(location: str) -> NormalizedLocation:
    # Supports either "city" or "locality, city" format.
    parts = [p.strip() for p in location.split(",") if p.strip()]
    if len(parts) == 1:
        city = _normalize_city(parts[0])
        return NormalizedLocation(city=city, locality=None)
    city = _normalize_city(parts[-1])
    locality = parts[0].title()
    return NormalizedLocation(city=city, locality=locality)


def _canonicalize_cuisines(cuisine: str | list[str]) -> list[str]:
    if isinstance(cuisine, str):
        tokens = [t.strip() for t in re.split(r"[,/|;]", cuisine) if t.strip()]
    else:
        tokens = []
        for item in cuisine:
            tokens.extend([t.strip() for t in re.split(r"[,/|;]", item) if t.strip()])

    canonical: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        key = token.lower()
        mapped = CUISINE_ALIASES.get(key, token.title())
        if mapped.lower() not in seen:
            seen.add(mapped.lower())
            canonical.append(mapped)
    return canonical


def _extract_tags(payload: PreferenceInput) -> list[str]:
    tags: set[str] = set()
    text_blobs: list[str] = []
    for value in [
        payload.free_text_notes,
        payload.party_type,
        payload.service_expectation,
        payload.dietary_preference,
    ]:
        if value:
            text_blobs.append(value.lower())
    corpus = " ".join(text_blobs)

    for tag, keywords in TAG_KEYWORDS.items():
        if any(keyword in corpus for keyword in keywords):
            tags.add(tag)

    # Explicit field-driven hints.
    if payload.party_type and payload.party_type.lower() == "family":
        tags.add("family-friendly")
    if payload.service_expectation and "quick" in payload.service_expectation.lower():
        tags.add("quick-service")

    return sorted(tags)


def normalize_preferences(payload: PreferenceInput) -> NormalizedPreference:
    normalized_location = _split_location(payload.location)
    budget_range = BudgetRange(
        min_cost_for_two=0,
        max_cost_for_two=payload.budget_amount,
        currency="INR",
    )
    canonical_cuisines = _canonicalize_cuisines(payload.cuisine)
    derived_tags = _extract_tags(payload)

    request_id = f"req_{uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()
    return NormalizedPreference(
        request_id=request_id,
        normalized_location=normalized_location,
        budget_amount=payload.budget_amount,
        budget_range=budget_range,
        canonical_cuisines=canonical_cuisines,
        min_rating=payload.min_rating,
        party_type=payload.party_type,
        service_expectation=payload.service_expectation,
        dietary_preference=payload.dietary_preference,
        derived_tags=derived_tags,
        created_at_utc=now,
    )
