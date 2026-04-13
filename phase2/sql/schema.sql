-- Canonical schema for Phase 2 ingestion output.

CREATE TABLE IF NOT EXISTS restaurants (
    restaurant_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    city TEXT NOT NULL,
    locality TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    avg_cost_for_two INTEGER NOT NULL,
    currency TEXT NOT NULL DEFAULT 'INR',
    price_band TEXT NOT NULL CHECK (price_band IN ('low', 'medium', 'high')),
    rating DOUBLE PRECISION NOT NULL CHECK (rating >= 0.0 AND rating <= 5.0),
    votes INTEGER,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    source_name TEXT NOT NULL,
    source_version TEXT NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, city, locality)
);

CREATE TABLE IF NOT EXISTS restaurant_cuisines (
    restaurant_id TEXT NOT NULL REFERENCES restaurants(restaurant_id) ON DELETE CASCADE,
    cuisine TEXT NOT NULL,
    PRIMARY KEY (restaurant_id, cuisine)
);

CREATE TABLE IF NOT EXISTS dataset_runs (
    run_id TEXT PRIMARY KEY,
    source_name TEXT NOT NULL,
    source_url TEXT NOT NULL,
    source_version TEXT NOT NULL,
    records_total INTEGER NOT NULL,
    records_loaded INTEGER NOT NULL,
    quality_report JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_restaurants_city_price_rating
ON restaurants (city, price_band, rating);

CREATE INDEX IF NOT EXISTS idx_restaurants_city_locality
ON restaurants (city, locality);
