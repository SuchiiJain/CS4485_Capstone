--CS4485 Capstone Database Schema
-- Tables will be added here

-- ============================================
-- Functions being tracked
-- ============================================

CREATE TABLE tracked_functions (
    id SERIAL PRIMARY KEY,
    stable_id TEXT UNIQUE NOT NULL,
    file_path TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- Fingerprints (store full fingerprint JSON)
-- ============================================

CREATE TABLE fingerprints (
    id SERIAL PRIMARY KEY,
    function_id INT REFERENCES tracked_functions(id) ON DELETE CASCADE,
    fingerprint_hash TEXT NOT NULL,
    fingerprint_data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- Change Events
-- ============================================

CREATE TABLE change_events (
    id SERIAL PRIMARY KEY,
    function_id INT REFERENCES tracked_functions(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    score INT NOT NULL,
    critical BOOLEAN DEFAULT FALSE,
    reasons JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- Doc Alerts
-- ============================================

CREATE TABLE doc_alerts (
    id SERIAL PRIMARY KEY,
    doc_path TEXT NOT NULL,
    message TEXT,
    cumulative_score INT,
    critical_found BOOLEAN,
    reasons JSONB,
    functions JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
