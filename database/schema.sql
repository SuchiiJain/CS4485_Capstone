--CS4485 Capstone Database Schema
-- Tables will be added here

-- ======================================================
-- Baseline Snapshot Per Repository
-- Mirrors .docrot-fingerprints.json exactly
-- ======================================================

-- One row per repository being tracked
CREATE TABLE baselines (
    id SERIAL PRIMARY KEY,
    repo_path TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- One row per file in that baseline
CREATE TABLE baseline_files (
    id SERIAL PRIMARY KEY,
    baseline_id INT NOT NULL REFERENCES baselines(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    UNIQUE (baseline_id, file_path)
);

-- One row per function in that file
CREATE TABLE function_fingerprints (
    id SERIAL PRIMARY KEY,
    baseline_file_id INT NOT NULL REFERENCES baseline_files(id) ON DELETE CASCADE,
    stable_id TEXT NOT NULL,
    fingerprint_hash TEXT NOT NULL,
    fingerprint_data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (baseline_file_id, stable_id)
);
