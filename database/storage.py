import os
import sqlite3
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "docrot.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    """Initialize database using schema.sql"""
    with get_connection() as conn:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())


def save_scan_report(commit_hash: str, report_json: str) -> None:
    """
    Store a completed scan report.
    Does NOT affect baseline logic.
    """
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO scan_reports (commit_hash, report_json)
            VALUES (?, ?)
            """,
            (commit_hash, report_json),
        )
        conn.commit()


def get_latest_report() -> Optional[str]:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT report_json
            FROM scan_reports
            ORDER BY created_at DESC
            LIMIT 1
            """
        ).fetchone()

        return row[0] if row else None
