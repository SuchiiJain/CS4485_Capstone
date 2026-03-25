-- ===============================
-- Docrot Detector Database Schema
-- ===============================

-- Legacy raw storage (kept for backwards compatibility)
CREATE TABLE IF NOT EXISTS scan_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    commit_hash TEXT NOT NULL,
    report_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Normalized scan metadata for dashboard/testing queries
CREATE TABLE IF NOT EXISTS scans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_path TEXT NOT NULL,
    commit_hash TEXT NOT NULL,
    status TEXT NOT NULL,
    total_issues INTEGER NOT NULL DEFAULT 0,
    high_count INTEGER NOT NULL DEFAULT 0,
    medium_count INTEGER NOT NULL DEFAULT 0,
    low_count INTEGER NOT NULL DEFAULT 0,
    report_timestamp TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- One row per reported issue/flag in .docrot-report.json
CREATE TABLE IF NOT EXISTS issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id INTEGER NOT NULL,
    reason TEXT,
    severity TEXT,
    code_element_name TEXT,
    code_file_path TEXT,
    signature TEXT,
    doc_file_path TEXT,
    message TEXT,
    suggestion TEXT,
    raw_issue_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (scan_id) REFERENCES scans(id)
);

-- Distinct documentation files to review for a scan
CREATE TABLE IF NOT EXISTS docs_to_update (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id INTEGER NOT NULL,
    doc_file_path TEXT NOT NULL,
    severity TEXT,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (scan_id) REFERENCES scans(id)
);

-- Persist generated artifacts by format (json/txt)
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id INTEGER NOT NULL,
    format TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (scan_id) REFERENCES scans(id)
);

-- Optional future use
-- Do NOT wire yet (baseline still JSON-based)
CREATE TABLE IF NOT EXISTS fingerprints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL,
    stable_id TEXT NOT NULL,
    fingerprint_hash TEXT NOT NULL,
    raw_data TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
