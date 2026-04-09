import os
import uuid
from datetime import datetime
import socket
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL not set.")
    # Force IPv4 only to avoid IPv6 connectivity issues
    old_getaddrinfo = socket.getaddrinfo
    def ipv4_only(*args, **kwargs):
        result = old_getaddrinfo(*args, **kwargs)
        return [r for r in result if r[0] == socket.AF_INET]
    socket.getaddrinfo = ipv4_only
    try:
        return psycopg2.connect(database_url, cursor_factory=RealDictCursor)
    finally:
        socket.getaddrinfo = old_getaddrinfo

def init_db():
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                CREATE TABLE IF NOT EXISTS scan_runs (
                    id UUID PRIMARY KEY,
                    repo_name TEXT,
                    commit_hash TEXT,
                    scanned_at TIMESTAMP WITH TIME ZONE,
                    total_issues INTEGER,
                    high_count INTEGER,
                    medium_count INTEGER,
                    low_count INTEGER
                )
                """)

                cur.execute("""
                CREATE TABLE IF NOT EXISTS flags (
                    id UUID PRIMARY KEY,
                    scan_id UUID REFERENCES scan_runs(id) ON DELETE CASCADE,
                    reason TEXT,
                    severity TEXT,
                    file_path TEXT,
                    symbol TEXT,
                    message TEXT,
                    suggestion TEXT
                )
                """)
    finally:
        conn.close()

def save_scan(repo_name, commit_hash, report_json):
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                scan_id = str(uuid.uuid4())
                meta = report_json.get("meta", {})
                severity = meta.get("severity_summary", {})

                cur.execute("""
                INSERT INTO scan_runs VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    scan_id,
                    repo_name,
                    commit_hash,
                    datetime.utcnow(),
                    meta.get("total_issues", 0),
                    severity.get("high", 0),
                    severity.get("medium", 0),
                    severity.get("low", 0),
                ))

                for issue in report_json.get("issues", []):
                    cur.execute("""
                    INSERT INTO flags VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
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
                return scan_id
    finally:
        conn.close()


def list_scans(repo_name: Optional[str], limit: int, offset: int) -> Tuple[List[Dict[str, Any]], int]:
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                if repo_name:
                    cur.execute(
                        "SELECT COUNT(*) AS cnt FROM scan_runs WHERE repo_name = %s",
                        (repo_name,),
                    )
                    total = int(cur.fetchone()["cnt"])
                    cur.execute(
                        """
                        SELECT
                            id,
                            repo_name AS repo_path,
                            commit_hash AS commit_sha,
                            'completed'::TEXT AS status,
                            (COALESCE(high_count, 0) * 5 + COALESCE(medium_count, 0) * 3 + COALESCE(low_count, 0))::INTEGER AS rot_score,
                            COALESCE(total_issues, 0)::INTEGER AS mismatch_count,
                            scanned_at AS created_at,
                            scanned_at AS updated_at,
                            total_issues,
                            high_count,
                            medium_count,
                            low_count
                        FROM scan_runs
                        WHERE repo_name = %s
                        ORDER BY scanned_at DESC
                        LIMIT %s OFFSET %s
                        """,
                        (repo_name, limit, offset),
                    )
                else:
                    cur.execute("SELECT COUNT(*) AS cnt FROM scan_runs")
                    total = int(cur.fetchone()["cnt"])
                    cur.execute(
                        """
                        SELECT
                            id,
                            repo_name AS repo_path,
                            commit_hash AS commit_sha,
                            'completed'::TEXT AS status,
                            (COALESCE(high_count, 0) * 5 + COALESCE(medium_count, 0) * 3 + COALESCE(low_count, 0))::INTEGER AS rot_score,
                            COALESCE(total_issues, 0)::INTEGER AS mismatch_count,
                            scanned_at AS created_at,
                            scanned_at AS updated_at,
                            total_issues,
                            high_count,
                            medium_count,
                            low_count
                        FROM scan_runs
                        ORDER BY scanned_at DESC
                        LIMIT %s OFFSET %s
                        """,
                        (limit, offset),
                    )

                return list(cur.fetchall()), total
    finally:
        conn.close()


def get_scan(scan_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        id,
                        repo_name AS repo_path,
                        commit_hash AS commit_sha,
                        'completed'::TEXT AS status,
                        (COALESCE(high_count, 0) * 5 + COALESCE(medium_count, 0) * 3 + COALESCE(low_count, 0))::INTEGER AS rot_score,
                        COALESCE(total_issues, 0)::INTEGER AS mismatch_count,
                        scanned_at AS created_at,
                        scanned_at AS updated_at,
                        total_issues,
                        high_count,
                        medium_count,
                        low_count
                    FROM scan_runs
                    WHERE id = %s
                    """,
                    (scan_id,),
                )
                return cur.fetchone()
    finally:
        conn.close()


def get_scan_issues(scan_id: str, severity: Optional[str], limit: int, offset: int) -> Tuple[List[Dict[str, Any]], int]:
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                if severity:
                    cur.execute(
                        "SELECT COUNT(*) AS cnt FROM flags WHERE scan_id = %s AND severity = %s",
                        (scan_id, severity),
                    )
                    total = int(cur.fetchone()["cnt"])
                    cur.execute(
                        """
                        SELECT id, scan_id, reason, severity, file_path, symbol, message, suggestion
                        FROM flags
                        WHERE scan_id = %s AND severity = %s
                        ORDER BY id DESC
                        LIMIT %s OFFSET %s
                        """,
                        (scan_id, severity, limit, offset),
                    )
                else:
                    cur.execute(
                        "SELECT COUNT(*) AS cnt FROM flags WHERE scan_id = %s",
                        (scan_id,),
                    )
                    total = int(cur.fetchone()["cnt"])
                    cur.execute(
                        """
                        SELECT id, scan_id, reason, severity, file_path, symbol, message, suggestion
                        FROM flags
                        WHERE scan_id = %s
                        ORDER BY id DESC
                        LIMIT %s OFFSET %s
                        """,
                        (scan_id, limit, offset),
                    )

                return list(cur.fetchall()), total
    finally:
        conn.close()


def get_repo_summary(repo_name: str) -> Dict[str, Any]:
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        COUNT(*)::INTEGER AS total_scans,
                        COALESCE(SUM(total_issues), 0)::INTEGER AS open_issues,
                        COALESCE(SUM(high_count), 0)::INTEGER AS high_issues,
                        COALESCE(SUM(medium_count), 0)::INTEGER AS medium_issues,
                        COALESCE(SUM(low_count), 0)::INTEGER AS low_issues
                    FROM scan_runs
                    WHERE repo_name = %s
                    """,
                    (repo_name,),
                )
                agg = cur.fetchone() or {}

                cur.execute(
                    """
                    SELECT
                        id AS latest_scan_id,
                        scanned_at AS latest_scan_at,
                        (COALESCE(high_count, 0) * 5 + COALESCE(medium_count, 0) * 3 + COALESCE(low_count, 0))::INTEGER AS latest_rot_score
                    FROM scan_runs
                    WHERE repo_name = %s
                    ORDER BY scanned_at DESC
                    LIMIT 1
                    """,
                    (repo_name,),
                )
                latest = cur.fetchone() or {}

                return {
                    "repo": repo_name,
                    "total_scans": agg.get("total_scans", 0),
                    "open_issues": agg.get("open_issues", 0),
                    "high_issues": agg.get("high_issues", 0),
                    "medium_issues": agg.get("medium_issues", 0),
                    "low_issues": agg.get("low_issues", 0),
                    "latest_rot_score": latest.get("latest_rot_score"),
                    "latest_scan_id": latest.get("latest_scan_id"),
                    "latest_scan_at": latest.get("latest_scan_at"),
                }
    finally:
        conn.close()