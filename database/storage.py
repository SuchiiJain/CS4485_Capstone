import os
import uuid
from datetime import datetime
import socket

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
    finally:
        conn.close()