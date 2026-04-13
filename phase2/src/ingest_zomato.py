import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from datasets import load_dataset
from sqlalchemy import create_engine, text

DATASET_ID = "ManikaSaini/zomato-restaurant-recommendation"
DATASET_URL = "https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation"
SOURCE_NAME = "huggingface_zomato_recommendation"

CITY_ALIASES = {
    "bangalore": "Bengaluru",
    "bengaluru": "Bengaluru",
    "new delhi": "Delhi",
    "delhi ncr": "Delhi",
    "bombay": "Mumbai",
}

COLUMN_ALIASES = {
    "name": [
        "restaurant_name",
        "name",
        "Restaurant Name",
        "res_name",
    ],
    "city": [
        "city",
        "City",
        "location",
        "Location",
    ],
    "locality": [
        "locality",
        "Locality",
        "address",
        "Address",
        "subzone",
        "Subzone",
    ],
    "cuisines": [
        "cuisines",
        "Cuisines",
        "cuisine",
        "Cuisine",
    ],
    "avg_cost_for_two": [
        "average_cost_for_two",
        "Average Cost for two",
        "cost_for_two",
        "Cost for Two",
        "approx_cost(for two people)",
        "price",
        "Price",
    ],
    "rating": [
        "aggregate_rating",
        "Aggregate rating",
        "rating",
        "Rating",
        "rate",
        "Rate",
    ],
    "votes": [
        "votes",
        "Votes",
        "num_votes",
    ],
    "latitude": ["latitude", "Latitude", "lat"],
    "longitude": ["longitude", "Longitude", "lon", "lng"],
}


@dataclass
class QualityReport:
    missing_name: int = 0
    missing_city: int = 0
    missing_cuisines: int = 0
    missing_cost: int = 0
    missing_rating: int = 0
    outlier_cost: int = 0
    outlier_rating: int = 0
    duplicate_records: int = 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest and normalize Zomato dataset.")
    parser.add_argument("--dataset-id", default=DATASET_ID, help="Hugging Face dataset id")
    parser.add_argument("--split", default="train", help="Dataset split")
    parser.add_argument(
        "--output-dir",
        default="phase2/data",
        help="Base output directory for raw and processed artifacts",
    )
    parser.add_argument("--run-id", default="", help="Optional ingestion run id")
    parser.add_argument(
        "--database-url",
        default="",
        help="Optional SQLAlchemy database URL for PostgreSQL upsert",
    )
    return parser.parse_args()


def pick_column(df: pd.DataFrame, canonical_name: str) -> str | None:
    candidates = COLUMN_ALIASES.get(canonical_name, [])
    columns_lookup = {col.lower(): col for col in df.columns}
    for alias in candidates:
        if alias.lower() in columns_lookup:
            return columns_lookup[alias.lower()]
    return None


def parse_float(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text_value = str(value).strip()
    if not text_value:
        return None

    match = re.search(r"\d+(\.\d+)?", text_value.replace(",", ""))
    if not match:
        return None
    return float(match.group(0))


def parse_int(value: Any) -> int | None:
    parsed = parse_float(value)
    if parsed is None:
        return None
    return int(round(parsed))


def normalize_city(raw_city: str | None) -> str | None:
    if not raw_city:
        return None
    city_clean = " ".join(raw_city.split()).strip()
    if not city_clean:
        return None
    mapped = CITY_ALIASES.get(city_clean.lower())
    return mapped or city_clean.title()


def normalize_cuisines(raw_cuisines: Any) -> list[str]:
    if raw_cuisines is None or (isinstance(raw_cuisines, float) and pd.isna(raw_cuisines)):
        return []
    if isinstance(raw_cuisines, list):
        cuisines_raw = [str(item) for item in raw_cuisines]
    else:
        cuisines_raw = re.split(r"[,/|;]", str(raw_cuisines))

    normalized: list[str] = []
    seen: set[str] = set()
    for item in cuisines_raw:
        token = " ".join(item.split()).strip()
        if not token:
            continue
        canonical = token.title()
        key = canonical.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(canonical)
    return normalized


def derive_price_band(cost_for_two: int) -> str:
    if cost_for_two <= 800:
        return "low"
    if cost_for_two <= 1800:
        return "medium"
    return "high"


def make_restaurant_id(name: str, city: str, locality: str | None) -> str:
    base = f"{name.strip().lower()}|{city.strip().lower()}|{(locality or '').strip().lower()}"
    digest = hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]
    return f"res_{digest}"


def load_hf_frame(dataset_id: str, split: str) -> pd.DataFrame:
    ds = load_dataset(dataset_id, split=split)
    return ds.to_pandas()


def validate_required_columns(df: pd.DataFrame) -> dict[str, str | None]:
    mapping: dict[str, str | None] = {}
    for canonical in ["name", "city", "cuisines", "avg_cost_for_two", "rating"]:
        mapping[canonical] = pick_column(df, canonical)
    missing = [field for field, col in mapping.items() if col is None]
    if missing:
        raise ValueError(
            f"Could not map required fields from source columns. Missing: {missing}. "
            f"Source columns: {list(df.columns)}"
        )

    for optional in ["locality", "votes", "latitude", "longitude"]:
        mapping[optional] = pick_column(df, optional)
    return mapping


def normalize_records(df: pd.DataFrame, field_map: dict[str, str | None]) -> tuple[pd.DataFrame, pd.DataFrame, QualityReport]:
    quality = QualityReport()
    restaurant_rows: list[dict[str, Any]] = []
    cuisine_rows: list[dict[str, str]] = []
    dedupe_seen: set[str] = set()

    for _, row in df.iterrows():
        name_raw = row[field_map["name"]] if field_map["name"] else None
        city_raw = row[field_map["city"]] if field_map["city"] else None
        cuisines_raw = row[field_map["cuisines"]] if field_map["cuisines"] else None
        cost_raw = row[field_map["avg_cost_for_two"]] if field_map["avg_cost_for_two"] else None
        rating_raw = row[field_map["rating"]] if field_map["rating"] else None
        locality_raw = row[field_map["locality"]] if field_map["locality"] else None
        votes_raw = row[field_map["votes"]] if field_map["votes"] else None
        lat_raw = row[field_map["latitude"]] if field_map["latitude"] else None
        lon_raw = row[field_map["longitude"]] if field_map["longitude"] else None

        name = None if pd.isna(name_raw) else str(name_raw).strip()
        city = normalize_city(None if pd.isna(city_raw) else str(city_raw))
        locality = None if locality_raw is None or pd.isna(locality_raw) else str(locality_raw).strip() or None
        cuisines = normalize_cuisines(cuisines_raw)
        cost_for_two = parse_int(cost_raw)
        rating = parse_float(rating_raw)
        votes = parse_int(votes_raw)
        latitude = parse_float(lat_raw)
        longitude = parse_float(lon_raw)

        if not name:
            quality.missing_name += 1
            continue
        if not city:
            quality.missing_city += 1
            continue
        if not cuisines:
            quality.missing_cuisines += 1
            continue
        if cost_for_two is None:
            quality.missing_cost += 1
            continue
        if rating is None:
            quality.missing_rating += 1
            continue

        if cost_for_two <= 0 or cost_for_two > 50000:
            quality.outlier_cost += 1
            continue
        if rating < 0.0 or rating > 5.0:
            quality.outlier_rating += 1
            continue

        dedupe_key = f"{name.lower()}|{city.lower()}|{(locality or '').lower()}"
        if dedupe_key in dedupe_seen:
            quality.duplicate_records += 1
            continue
        dedupe_seen.add(dedupe_key)

        restaurant_id = make_restaurant_id(name=name, city=city, locality=locality)
        price_band = derive_price_band(cost_for_two)

        restaurant_rows.append(
            {
                "restaurant_id": restaurant_id,
                "name": name,
                "city": city,
                "locality": locality,
                "latitude": latitude,
                "longitude": longitude,
                "avg_cost_for_two": cost_for_two,
                "currency": "INR",
                "price_band": price_band,
                "rating": round(rating, 2),
                "votes": votes,
                "is_active": True,
            }
        )

        for cuisine in cuisines:
            cuisine_rows.append({"restaurant_id": restaurant_id, "cuisine": cuisine})

    restaurants_df = pd.DataFrame(restaurant_rows)
    cuisines_df = pd.DataFrame(cuisine_rows).drop_duplicates()
    return restaurants_df, cuisines_df, quality


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def persist_raw_snapshot(df: pd.DataFrame, raw_dir: Path, split: str) -> None:
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / f"raw_{split}.jsonl"
    df.to_json(raw_path, orient="records", lines=True, force_ascii=False)


def persist_processed(
    restaurants_df: pd.DataFrame,
    cuisines_df: pd.DataFrame,
    processed_dir: Path,
) -> None:
    processed_dir.mkdir(parents=True, exist_ok=True)
    restaurants_df.to_csv(processed_dir / "restaurants.csv", index=False)
    cuisines_df.to_csv(processed_dir / "restaurant_cuisines.csv", index=False)


def apply_schema(conn, schema_file: Path) -> None:
    ddl = schema_file.read_text(encoding="utf-8")
    for statement in ddl.split(";"):
        chunk = statement.strip()
        if chunk:
            conn.execute(text(chunk))


def upsert_postgres(
    database_url: str,
    restaurants_df: pd.DataFrame,
    cuisines_df: pd.DataFrame,
    dataset_run: dict[str, Any],
) -> None:
    schema_file = Path(__file__).resolve().parents[1] / "sql" / "schema.sql"
    engine = create_engine(database_url, future=True)

    with engine.begin() as conn:
        apply_schema(conn, schema_file)

        conn.execute(
            text(
                """
                INSERT INTO dataset_runs (
                    run_id, source_name, source_url, source_version, records_total, records_loaded, quality_report
                ) VALUES (
                    :run_id, :source_name, :source_url, :source_version, :records_total, :records_loaded, CAST(:quality_report AS JSONB)
                )
                ON CONFLICT (run_id) DO UPDATE SET
                    source_name = EXCLUDED.source_name,
                    source_url = EXCLUDED.source_url,
                    source_version = EXCLUDED.source_version,
                    records_total = EXCLUDED.records_total,
                    records_loaded = EXCLUDED.records_loaded,
                    quality_report = EXCLUDED.quality_report
                """
            ),
            {
                "run_id": dataset_run["run_id"],
                "source_name": dataset_run["source_name"],
                "source_url": dataset_run["source_url"],
                "source_version": dataset_run["source_version"],
                "records_total": dataset_run["records_total"],
                "records_loaded": dataset_run["records_loaded"],
                "quality_report": json.dumps(dataset_run["quality_report"]),
            },
        )

        restaurant_sql = text(
            """
            INSERT INTO restaurants (
                restaurant_id, name, city, locality, latitude, longitude, avg_cost_for_two, currency,
                price_band, rating, votes, is_active, source_name, source_version
            ) VALUES (
                :restaurant_id, :name, :city, :locality, :latitude, :longitude, :avg_cost_for_two, :currency,
                :price_band, :rating, :votes, :is_active, :source_name, :source_version
            )
            ON CONFLICT (restaurant_id) DO UPDATE SET
                name = EXCLUDED.name,
                city = EXCLUDED.city,
                locality = EXCLUDED.locality,
                latitude = EXCLUDED.latitude,
                longitude = EXCLUDED.longitude,
                avg_cost_for_two = EXCLUDED.avg_cost_for_two,
                currency = EXCLUDED.currency,
                price_band = EXCLUDED.price_band,
                rating = EXCLUDED.rating,
                votes = EXCLUDED.votes,
                is_active = EXCLUDED.is_active,
                source_name = EXCLUDED.source_name,
                source_version = EXCLUDED.source_version,
                updated_at = CURRENT_TIMESTAMP
            """
        )

        restaurant_payload = []
        for _, record in restaurants_df.iterrows():
            entry = record.to_dict()
            entry["source_name"] = dataset_run["source_name"]
            entry["source_version"] = dataset_run["source_version"]
            restaurant_payload.append(entry)
        conn.execute(restaurant_sql, restaurant_payload)

        cuisine_sql = text(
            """
            INSERT INTO restaurant_cuisines (restaurant_id, cuisine)
            VALUES (:restaurant_id, :cuisine)
            ON CONFLICT (restaurant_id, cuisine) DO NOTHING
            """
        )
        conn.execute(cuisine_sql, cuisines_df.to_dict(orient="records"))


def build_dataset_run(
    run_id: str,
    records_total: int,
    records_loaded: int,
    quality: QualityReport,
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "source_name": SOURCE_NAME,
        "source_url": DATASET_URL,
        "source_version": f"snapshot_{datetime.now(timezone.utc).date()}",
        "records_total": records_total,
        "records_loaded": records_loaded,
        "quality_report": asdict(quality),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def main() -> None:
    args = parse_args()
    now = datetime.now(timezone.utc)
    run_id = args.run_id or f"run_{now.strftime('%Y%m%d_%H%M%S')}"
    date_part = now.strftime("%Y-%m-%d")

    base_output = Path(args.output_dir)
    raw_dir = base_output / "raw" / date_part / run_id
    processed_dir = base_output / "processed" / date_part / run_id

    print(f"[Phase2] Loading dataset '{args.dataset_id}' split='{args.split}'")
    raw_df = load_hf_frame(args.dataset_id, args.split)
    print(f"[Phase2] Loaded records: {len(raw_df)}")

    field_map = validate_required_columns(raw_df)
    persist_raw_snapshot(raw_df, raw_dir, args.split)

    restaurants_df, cuisines_df, quality = normalize_records(raw_df, field_map)
    persist_processed(restaurants_df, cuisines_df, processed_dir)

    dataset_run = build_dataset_run(
        run_id=run_id,
        records_total=len(raw_df),
        records_loaded=len(restaurants_df),
        quality=quality,
    )
    write_json(processed_dir / "dataset_run.json", dataset_run)
    write_json(processed_dir / "field_mapping.json", field_map)

    print(f"[Phase2] Records loaded after cleaning: {len(restaurants_df)}")
    print(f"[Phase2] Raw snapshot: {raw_dir}")
    print(f"[Phase2] Processed artifacts: {processed_dir}")

    if args.database_url:
        print("[Phase2] Upserting into PostgreSQL...")
        upsert_postgres(args.database_url, restaurants_df, cuisines_df, dataset_run)
        print("[Phase2] PostgreSQL upsert complete.")
    else:
        print("[Phase2] Skipped database upsert (no --database-url provided).")


if __name__ == "__main__":
    main()
