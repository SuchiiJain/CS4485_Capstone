import sqlite3
import uuid
from datetime import datetime

DB_PATH = "backend/docrot.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS scan_runs (
        id TEXT PRIMARY KEY,
        repo_name TEXT,
        commit_hash TEXT,
        scanned_at TEXT,
        total_issues INTEGER,
        high_count INTEGER,
        medium_count INTEGER,
        low_count INTEGER
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS flags (
        id TEXT PRIMARY KEY,
        scan_id TEXT,
        reason TEXT,
        severity TEXT,
        file_path TEXT,
        symbol TEXT,
        message TEXT,
        suggestion TEXT,
        FOREIGN KEY(scan_id) REFERENCES scan_runs(id)
    )
    """)

    conn.commit()
    conn.close()


def save_scan(repo_name, commit_hash, report_json):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    scan_id = str(uuid.uuid4())
    meta = report_json.get("meta", {})
    severity = meta.get("severity_summary", {})

    cur.execute("""
    INSERT INTO scan_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        scan_id,
        repo_name,
        commit_hash,
        datetime.utcnow().isoformat(),
        meta.get("total_issues", 0),
        severity.get("high", 0),
        severity.get("medium", 0),
        severity.get("low", 0),
    ))

    for issue in report_json.get("issues", []):
        cur.execute("""
        INSERT INTO flags VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()),
            scan_id,
            issue["reason"],
            issue["severity"],
            issue["code_element"]["file_path"],
            issue["code_element"]["name"],
            issue["message"],
            issue.get("suggestion"),
        ))

    conn.commit()
    conn.close()
