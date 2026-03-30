-- ============================================================
-- Docrot Detector Database Schema
-- Designed for Postgres (Supabase)
-- ============================================================

-- ============================================================
-- 1. REPOS
-- One row per tracked repository
-- ============================================================

CREATE TABLE IF NOT EXISTS repos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name TEXT UNIQUE NOT NULL,          -- "owner/repo"
    github_url TEXT,
    first_seen_at TIMESTAMPTZ DEFAULT now(),
    latest_scan_id UUID                      -- updated after each scan
);


-- ============================================================
-- 2. SCAN RUNS
-- One record per pipeline execution
-- ============================================================

CREATE TABLE IF NOT EXISTS scan_runs (
    id UUID PRIMARY KEY,
    repo_name TEXT NOT NULL,
    commit_hash TEXT NOT NULL,
    branch TEXT,
    status TEXT DEFAULT 'unknown',           -- "clean" | "issues_found"
    scanned_at TIMESTAMPTZ DEFAULT now(),

    total_issues INTEGER DEFAULT 0,
    high_count INTEGER DEFAULT 0,
    medium_count INTEGER DEFAULT 0,
    low_count INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_scan_repo
ON scan_runs (repo_name, scanned_at DESC);


-- ============================================================
-- 3. FLAGS
-- One record per issue detected in a scan
-- ============================================================

CREATE TABLE IF NOT EXISTS flags (
    id UUID PRIMARY KEY,
    scan_id UUID NOT NULL REFERENCES scan_runs(id) ON DELETE CASCADE,

    reason TEXT NOT NULL,
    severity TEXT NOT NULL,

    file_path TEXT,
    symbol TEXT,

    message TEXT,
    suggestion TEXT,

    signature TEXT,                           -- full function signature
    params TEXT,                              -- JSON array of param names
    return_type TEXT,

    doc_file TEXT,                            -- flagged documentation file
    doc_symbol TEXT                           -- symbol referenced in the doc
);

CREATE INDEX IF NOT EXISTS idx_flags_scan
ON flags (scan_id);


-- ============================================================
-- 4. FOREIGN KEY: repos.latest_scan_id -> scan_runs
-- Added after both tables exist
-- ============================================================

ALTER TABLE repos
    ADD CONSTRAINT fk_repos_latest_scan
    FOREIGN KEY (latest_scan_id) REFERENCES scan_runs(id)
    ON DELETE SET NULL;


-- ============================================================
-- 5. ROW LEVEL SECURITY
-- ============================================================

ALTER TABLE repos ENABLE ROW LEVEL SECURITY;
ALTER TABLE scan_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE flags ENABLE ROW LEVEL SECURITY;

-- Anon can insert and upsert repos (for latest_scan_id updates)
CREATE POLICY "Allow anon insert" ON repos FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY "Allow anon update" ON repos FOR UPDATE TO anon USING (true) WITH CHECK (true);

-- Anon can insert scans and flags
CREATE POLICY "Allow anon insert" ON scan_runs FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY "Allow anon insert" ON flags FOR INSERT TO anon WITH CHECK (true);
