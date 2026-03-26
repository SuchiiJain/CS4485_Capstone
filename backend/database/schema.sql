-- ============================================================
-- Docrot Detector Database Schema
-- Designed for Postgres (Supabase-ready)
-- Also compatible with SQLite (minor syntax differences)
-- ============================================================

-- ============================================================
-- 1. SCAN RUNS
-- One record per pipeline execution
-- ============================================================

CREATE TABLE IF NOT EXISTS scan_runs (
    id TEXT PRIMARY KEY,                     -- UUID
    repo_name TEXT NOT NULL,
    commit_hash TEXT NOT NULL,
    scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    total_issues INTEGER DEFAULT 0,
    high_count INTEGER DEFAULT 0,
    medium_count INTEGER DEFAULT 0,
    low_count INTEGER DEFAULT 0
);

-- Index for querying latest scans per repo
CREATE INDEX IF NOT EXISTS idx_scan_repo
ON scan_runs (repo_name, scanned_at DESC);


-- ============================================================
-- 2. FUNCTION FLAGS
-- One record per issue detected in a scan
-- ============================================================

CREATE TABLE IF NOT EXISTS flags (
    id TEXT PRIMARY KEY,                     -- UUID
    scan_id TEXT NOT NULL,

    reason TEXT NOT NULL,
    severity TEXT NOT NULL,

    file_path TEXT,
    symbol TEXT,

    message TEXT,
    suggestion TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (scan_id)
        REFERENCES scan_runs(id)
        ON DELETE CASCADE
);

-- Index for fast lookup of flags per scan
CREATE INDEX IF NOT EXISTS idx_flags_scan
ON flags (scan_id);


-- ============================================================
-- 3. FINGERPRINT BASELINE (Optional Future Use)
-- Keeps baseline in DB instead of JSON file
-- ============================================================

CREATE TABLE IF NOT EXISTS fingerprints (
    id TEXT PRIMARY KEY,                     -- UUID
    repo_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    stable_id TEXT NOT NULL,
    fingerprint_hash TEXT NOT NULL,
    fingerprint_json TEXT NOT NULL,          -- JSONB if Postgres
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Prevent duplicate function entries per repo
CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_fingerprint
ON fingerprints (repo_name, file_path, stable_id);
