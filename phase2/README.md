# Phase 2 Implementation: Data Ingestion and Standardization

This folder implements Phase 2 from `phase_wise_architecture.md`.

## What is implemented
- Pulls dataset from Hugging Face:
  - `https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation`
- Stores raw dataset snapshot by date and run ID.
- Maps source columns to canonical fields.
- Normalizes location, cuisines, cost, and rating.
- Runs data quality checks:
  - missing critical fields
  - cost/rating outliers
  - duplicate records
- Produces processed outputs:
  - `restaurants.csv`
  - `restaurant_cuisines.csv`
  - `dataset_run.json`
- Optionally upserts into PostgreSQL using canonical schema.

## Folder structure
- `data/raw/`: Hugging Face snapshots (not committed to Git — often over 100MB; run ingestion locally).
- `src/ingest_zomato.py`: main ingestion + normalization + optional DB upsert.
- `sql/schema.sql`: canonical relational schema.
- `requirements.txt`: Python dependencies for this phase.

## Quick start

### 1) Install dependencies
```powershell
python -m pip install -r phase2/requirements.txt
```

### 2) Run ingestion (files only)
```powershell
python phase2/src/ingest_zomato.py
```

### 3) Run ingestion + PostgreSQL upsert
```powershell
python phase2/src/ingest_zomato.py --database-url "postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME"
```

## Output location
By default, outputs are written under:
- `phase2/data/raw/YYYY-MM-DD/<run_id>/`
- `phase2/data/processed/YYYY-MM-DD/<run_id>/`

## Notes
- The script auto-detects common source column names and fails with clear errors if critical fields cannot be mapped.
- `restaurant_id` is deterministic (hash-based) so repeated runs produce stable IDs and support upsert behavior.
