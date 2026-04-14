from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from phase3.src.preference_service import NormalizedPreference


@dataclass
class CandidateResult:
    request_id: str
    total_candidates: int
    top_n: int
    candidates: list[dict[str, Any]]


class RetrievalService:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.cache_ttl_seconds = max(0.0, float(os.getenv("RETRIEVAL_CACHE_TTL_SECONDS", "20")))
        self.cache: dict[str, tuple[float, CandidateResult]] = {}
        self.loaded_run_dir: Path | None = None
        self.loaded_run_mtime: float = 0.0
        self.restaurants_df = pd.DataFrame()
        self.cuisines_df = pd.DataFrame()
        self.tag_index: dict[str, set[str]] = {}
        self.cuisine_index: dict[str, list[str]] = {}
        self._reload_processed_data(force=True)
        self.metro_city_tokens = {"bengaluru", "bangalore", "delhi", "mumbai", "hyderabad", "chennai"}

    @staticmethod
    def _metro_address_patterns(metro_key: str) -> list[str]:
        """Substrings to match in `locality` (often a full address) when the user names a metro."""
        key = metro_key.lower()
        mapping: dict[str, list[str]] = {
            "bengaluru": ["bangalore", "bengaluru"],
            "bangalore": ["bangalore", "bengaluru"],
            "mumbai": ["mumbai", "bombay"],
            "delhi": ["delhi", "new delhi", "ncr", "gurgaon", "gurugram", "noida"],
            "hyderabad": ["hyderabad", "secunderabad"],
            "chennai": ["chennai", "madras"],
        }
        return mapping.get(key, [key])

    def _rows_matching_area(self, frame: pd.DataFrame, area_token: str) -> pd.DataFrame:
        """Match neighborhood name in `city` or as a substring of the address `locality` column."""
        if not area_token or not str(area_token).strip():
            return frame
        t = str(area_token).strip().lower()
        city_eq = frame["city"] == t
        if len(t) >= 3:
            loc = frame["locality"].fillna("").astype(str).str.lower()
            sub = loc.str.contains(re.escape(t), na=False, regex=True)
            mask = city_eq | sub
        else:
            mask = city_eq
        return frame[mask]

    def _latest_processed_run_dir(self) -> Path:
        base = self.project_root / "phase2" / "data" / "processed"
        if not base.exists():
            raise FileNotFoundError("Phase 2 processed data folder not found.")
        run_dirs = sorted(
            [p for p in base.glob("*/*") if p.is_dir()],
            key=lambda x: x.stat().st_mtime,
        )
        if not run_dirs:
            raise FileNotFoundError("No processed run found. Run phase2 ingestion first.")
        return run_dirs[-1]

    def _load_processed_data(self, run_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
        restaurants_path = run_dir / "restaurants.csv"
        cuisines_path = run_dir / "restaurant_cuisines.csv"
        if not restaurants_path.exists() or not cuisines_path.exists():
            raise FileNotFoundError("Processed CSV files missing in latest run.")

        restaurants_df = pd.read_csv(restaurants_path)
        cuisines_df = pd.read_csv(cuisines_path)
        restaurants_df["city"] = restaurants_df["city"].astype(str).str.strip().str.lower()
        restaurants_df["locality"] = restaurants_df["locality"].fillna("").astype(str).str.strip().str.lower()
        restaurants_df["rating"] = pd.to_numeric(restaurants_df["rating"], errors="coerce").fillna(0.0)
        restaurants_df["avg_cost_for_two"] = pd.to_numeric(
            restaurants_df["avg_cost_for_two"], errors="coerce"
        ).fillna(0)
        restaurants_df["votes"] = pd.to_numeric(restaurants_df["votes"], errors="coerce").fillna(0)
        cuisines_df["cuisine"] = cuisines_df["cuisine"].astype(str).str.strip().str.lower()
        return restaurants_df, cuisines_df

    def _reload_processed_data(self, force: bool = False) -> None:
        run_dir = self._latest_processed_run_dir()
        run_mtime = run_dir.stat().st_mtime
        if (
            not force
            and self.loaded_run_dir is not None
            and run_dir == self.loaded_run_dir
            and run_mtime <= self.loaded_run_mtime
        ):
            return

        restaurants_df, cuisines_df = self._load_processed_data(run_dir)
        self.restaurants_df = restaurants_df
        self.cuisines_df = cuisines_df
        self.tag_index = self._build_tag_index(self.cuisines_df)
        self.cuisine_index = self.cuisines_df.groupby("restaurant_id")["cuisine"].apply(list).to_dict()
        self.loaded_run_dir = run_dir
        self.loaded_run_mtime = run_mtime
        self.cache.clear()

    def _cache_get(self, key: str) -> CandidateResult | None:
        cached = self.cache.get(key)
        if not cached:
            return None
        created_at, value = cached
        if self.cache_ttl_seconds and (time.monotonic() - created_at > self.cache_ttl_seconds):
            self.cache.pop(key, None)
            return None
        return value

    def _cache_set(self, key: str, value: CandidateResult) -> None:
        if self.cache_ttl_seconds <= 0:
            return
        self.cache[key] = (time.monotonic(), value)

    def _build_tag_index(self, cuisines_df: pd.DataFrame) -> dict[str, set[str]]:
        cuisine_map = cuisines_df.groupby("restaurant_id")["cuisine"].apply(set).to_dict()
        tag_index: dict[str, set[str]] = {}
        for restaurant_id, cuisines in cuisine_map.items():
            tags = set()
            if any("veg" in c for c in cuisines):
                tags.add("vegetarian-options")
            if any("vegan" in c for c in cuisines):
                tags.add("vegan-options")
            if any(c in {"fast food", "street food", "burger", "pizza"} for c in cuisines):
                tags.add("quick-service")
            tag_index[restaurant_id] = tags
        return tag_index

    def _cache_key(self, pref: NormalizedPreference, top_n: int) -> str:
        return "|".join(
            [
                pref.normalized_location.city.lower(),
                (pref.normalized_location.locality or "").lower(),
                str(pref.budget_amount),
                ",".join(sorted([c.lower() for c in pref.canonical_cuisines])),
                str(pref.min_rating),
                ",".join(sorted(pref.derived_tags)),
                str(top_n),
            ]
        )

    def _score_row(
        self,
        row: pd.Series,
        requested_cuisines: set[str],
        requested_tags: set[str],
        max_votes: float,
    ) -> dict[str, float]:
        rating_norm = min(max(float(row["rating"]) / 5.0, 0.0), 1.0)

        row_cuisines = set(
            self.cuisines_df[self.cuisines_df["restaurant_id"] == row["restaurant_id"]]["cuisine"].tolist()
        )
        cuisine_match = (
            len(requested_cuisines.intersection(row_cuisines)) / len(requested_cuisines)
            if requested_cuisines
            else 0.0
        )

        min_budget = float(row["budget_min"])
        max_budget = float(row["budget_max"])
        cost = float(row["avg_cost_for_two"])
        budget_fit = 1.0 if min_budget <= cost <= max_budget else 0.0

        popularity = 0.0 if max_votes <= 0 else min(float(row["votes"]) / max_votes, 1.0)

        row_tags = self.tag_index.get(row["restaurant_id"], set())
        tag_overlap = (
            len(requested_tags.intersection(row_tags)) / len(requested_tags) if requested_tags else 0.0
        )
        cuisine_match = min(cuisine_match + (0.1 * tag_overlap), 1.0)

        final_score = (
            0.35 * rating_norm
            + 0.30 * cuisine_match
            + 0.20 * budget_fit
            + 0.15 * popularity
        )

        return {
            "score": round(final_score, 6),
            "rating_norm": round(rating_norm, 6),
            "cuisine_match": round(cuisine_match, 6),
            "budget_fit": round(budget_fit, 6),
            "popularity": round(popularity, 6),
            "tag_overlap": round(tag_overlap, 6),
        }

    def list_localities(self) -> list[str]:
        """Distinct area/locality names from catalog (`city` column holds area in this dataset), sorted."""
        self._reload_processed_data()
        keys: set[str] = set()
        for raw in self.restaurants_df["city"].dropna().unique():
            token = str(raw).strip().lower()
            if token:
                keys.add(token)
        return sorted((k.title() for k in keys), key=str.lower)

    def list_cuisines(self) -> list[str]:
        """Distinct cuisine labels that appear on at least one restaurant in the loaded catalog."""
        self._reload_processed_data()
        valid_ids = set(self.restaurants_df["restaurant_id"].astype(str).str.strip())
        keys: set[str] = set()
        for _, row in self.cuisines_df.iterrows():
            rid = str(row.get("restaurant_id", "")).strip()
            if rid not in valid_ids:
                continue
            raw = row.get("cuisine")
            if raw is None or (isinstance(raw, float) and pd.isna(raw)):
                continue
            token = str(raw).strip().lower()
            if token:
                keys.add(token)
        return sorted((k.title() for k in keys), key=str.lower)

    def retrieve_candidates(self, pref: NormalizedPreference, top_n: int = 30) -> CandidateResult:
        self._reload_processed_data()
        top_n = max(1, min(top_n, 50))
        key = self._cache_key(pref, top_n)
        cached = self._cache_get(key)
        if cached:
            return cached

        city = pref.normalized_location.city.lower()
        locality = (pref.normalized_location.locality or "").lower()
        min_rating = pref.min_rating
        budget_min = pref.budget_range.min_cost_for_two
        budget_max = pref.budget_range.max_cost_for_two

        df = self.restaurants_df.copy()
        df["budget_min"] = budget_min
        df["budget_max"] = budget_max

        filtered = df[df["city"] == city]
        if filtered.empty:
            # Some datasets store neighborhood names in `city` and metro only in addresses.
            if city in self.metro_city_tokens:
                patterns = self._metro_address_patterns(city)
                loc_all = df["locality"].fillna("").astype(str).str.lower()
                pat = "|".join(re.escape(p) for p in patterns)
                metro_mask = loc_all.str.contains(pat, na=False, regex=True)
                filtered = df[metro_mask] if metro_mask.any() else df
            elif locality:
                filtered = self._rows_matching_area(df, locality)

        if locality:
            narrowed = self._rows_matching_area(filtered, locality)
            if not narrowed.empty:
                filtered = narrowed
        filtered = filtered[filtered["rating"] >= min_rating]
        filtered = filtered[
            (filtered["avg_cost_for_two"] >= budget_min) & (filtered["avg_cost_for_two"] <= budget_max)
        ]

        requested_cuisines = {c.lower() for c in pref.canonical_cuisines}
        # Common catalog synonyms (Zomato-style tags) so a user-facing label still matches rows.
        for c in list(requested_cuisines):
            if c == "chinese":
                requested_cuisines.update({"indo-chinese", "momos", "sichuan"})
            elif c == "italian":
                requested_cuisines.add("pizza")
            elif c == "north indian":
                requested_cuisines.update({"mughlai", "biryani", "kebab", "awadhi", "lucknowi"})
        if requested_cuisines:
            cuisine_hit = self.cuisines_df["cuisine"].str.lower().isin(requested_cuisines)
            allowed_ids = set(
                self.cuisines_df.loc[cuisine_hit, "restaurant_id"].astype(str).str.strip()
            )
            rid = filtered["restaurant_id"].astype(str).str.strip()
            filtered = filtered[rid.isin(allowed_ids)]

        if filtered.empty:
            result = CandidateResult(
                request_id=pref.request_id,
                total_candidates=0,
                top_n=top_n,
                candidates=[],
            )
            self._cache_set(key, result)
            return result

        max_votes = float(filtered["votes"].max()) if not filtered.empty else 0.0
        requested_tags = set(pref.derived_tags)

        scored_rows: list[dict[str, Any]] = []
        for _, row in filtered.iterrows():
            metrics = self._score_row(row, requested_cuisines, requested_tags, max_votes)
            scored_rows.append(
                {
                    "restaurant_id": row["restaurant_id"],
                    "name": row["name"],
                    "cuisines": [c.title() for c in self.cuisine_index.get(row["restaurant_id"], [])],
                    "city": row["city"].title(),
                    "locality": None if not row["locality"] else str(row["locality"]).title(),
                    "rating": round(float(row["rating"]), 2),
                    "avg_cost_for_two": int(row["avg_cost_for_two"]),
                    "price_band": row["price_band"],
                    "votes": int(row["votes"]),
                    "scoring": metrics,
                }
            )

        ranked = sorted(scored_rows, key=lambda x: x["scoring"]["score"], reverse=True)[:top_n]
        for index, item in enumerate(ranked, start=1):
            item["rank"] = index

        result = CandidateResult(
            request_id=pref.request_id,
            total_candidates=len(scored_rows),
            top_n=top_n,
            candidates=ranked,
        )
        self._cache_set(key, result)
        return result

    def top_restaurants_by_locality(self, locality: str, limit: int = 5) -> list[dict[str, Any]]:
        self._reload_processed_data()
        token = (locality or "").strip().lower()
        if not token:
            return []

        limit = max(1, min(int(limit), 10))
        filtered = self._rows_matching_area(self.restaurants_df, token)
        if filtered.empty:
            return []

        ranked = filtered.sort_values(by=["rating", "votes"], ascending=[False, False]).head(limit)
        items: list[dict[str, Any]] = []
        for _, row in ranked.iterrows():
            rid = str(row["restaurant_id"]).strip()
            items.append(
                {
                    "restaurant_id": rid,
                    "restaurant_name": row["name"],
                    "cuisine": [c.title() for c in self.cuisine_index.get(rid, [])],
                    "rating": round(float(row["rating"]), 2),
                    "estimated_cost": int(row["avg_cost_for_two"]),
                    "currency": "INR",
                    "votes": int(row["votes"]),
                    "locality": None if not row["locality"] else str(row["locality"]).title(),
                    "city": str(row["city"]).title(),
                }
            )
        return items
