-- Migration: Add locations and vegetation_data tables for NDVI integration

-- Create locations table
CREATE TABLE IF NOT EXISTS locations (
    id SERIAL PRIMARY KEY,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    CONSTRAINT uq_location_lat_lng UNIQUE (latitude, longitude)
);

-- Index for fast coordinate lookups
CREATE INDEX IF NOT EXISTS ix_location_lat_lng ON locations (latitude, longitude);

-- Create vegetation_data table for independent NDVI storage
CREATE TABLE IF NOT EXISTS vegetation_data (
    id SERIAL PRIMARY KEY,
    location_id INTEGER NOT NULL,
    ndvi DOUBLE PRECISION NOT NULL,
    source VARCHAR(50),
    captured_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_vegetation_location FOREIGN KEY (location_id) REFERENCES locations (id) ON DELETE CASCADE
);

-- Index for retrieving the most recent NDVI value for a specific location
CREATE INDEX IF NOT EXISTS ix_vegetation_data_location_id_captured_at ON vegetation_data (location_id, captured_at DESC);
