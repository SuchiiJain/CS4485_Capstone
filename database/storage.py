import os
import sqlite3
import json
from typing import Any, Dict, List, Optional

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "docrot.db")
DB_PATH = DEFAULT_DB_PATH
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


def get_db_path() -> str:
    """Return DB path, allowing override for CI/webhook environments."""
    return os.environ.get("DOCROT_DB_PATH", DEFAULT_DB_PATH)


def get_connection():
    return sqlite3.connect(get_db_path())


def init_db():
    """Initialize database using schema.sql"""
    with get_connection() as conn:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())


def save_normalized_scan_report(commit_hash: str, report_payload: Dict[str, Any]) -> int:
    """
    Persist a report as normalized scan/issues/docs/reports rows.

    Returns:
        Inserted scan ID.
    """
    meta = report_payload.get("meta", {}) if isinstance(report_payload, dict) else {}
    issues = report_payload.get("issues", []) if isinstance(report_payload, dict) else []

    repo_path = str(meta.get("repo_path", "unknown"))
    total_issues = int(meta.get("total_issues", 0) or 0)
    sev = meta.get("severity_summary", {}) if isinstance(meta.get("severity_summary"), dict) else {}
    high_count = int(sev.get("high", 0) or 0)
    medium_count = int(sev.get("medium", 0) or 0)
    low_count = int(sev.get("low", 0) or 0)
    report_timestamp = meta.get("timestamp")
    status = "completed_with_issues" if total_issues > 0 else "completed"

    with get_connection() as conn:
        cur = conn.cursor()

        # Keep legacy raw table for compatibility.
        cur.execute(
            """
            INSERT INTO scan_reports (commit_hash, report_json)
            VALUES (?, ?)
            """,
            (commit_hash, json.dumps(report_payload)),
        )

        cur.execute(
            """
            INSERT INTO scans (
                repo_path,
                commit_hash,
                status,
                total_issues,
                high_count,
                medium_count,
                low_count,
                report_timestamp
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                repo_path,
                commit_hash,
                status,
                total_issues,
                high_count,
                medium_count,
                low_count,
                report_timestamp,
            ),
        )
        scan_id = int(cur.lastrowid)

        cur.execute(
            """
            INSERT INTO reports (scan_id, format, content)
            VALUES (?, ?, ?)
            """,
            (scan_id, "json", json.dumps(report_payload)),
        )

        docs_seen = set()
        if isinstance(issues, list):
            for issue in issues:
                if not isinstance(issue, dict):
                    continue

                code_element = issue.get("code_element") or {}
                if not isinstance(code_element, dict):
                    code_element = {}

                doc_ref = issue.get("doc_reference") or {}
                if not isinstance(doc_ref, dict):
                    doc_ref = {}

                doc_file_path = doc_ref.get("file_path")
                # Doc-file alerts use code_element.file_path to carry the doc path.
                if not doc_file_path:
                    possible_doc = code_element.get("file_path")
                    if isinstance(possible_doc, str) and possible_doc.lower().endswith((".md", ".txt", ".rst")):
                        doc_file_path = possible_doc

                cur.execute(
                    """
                    INSERT INTO issues (
                        scan_id,
                        reason,
                        severity,
                        code_element_name,
                        code_file_path,
                        signature,
                        doc_file_path,
                        message,
                        suggestion,
                        raw_issue_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        scan_id,
                        issue.get("reason"),
                        issue.get("severity"),
                        code_element.get("name"),
                        code_element.get("file_path"),
                        code_element.get("signature"),
                        doc_file_path,
                        issue.get("message"),
                        issue.get("suggestion"),
                        json.dumps(issue),
                    ),
                )

                if doc_file_path and doc_file_path not in docs_seen:
                    docs_seen.add(doc_file_path)
                    cur.execute(
                        """
                        INSERT INTO docs_to_update (scan_id, doc_file_path, severity, reason)
                        VALUES (?, ?, ?, ?)
                        """,
                        (scan_id, doc_file_path, issue.get("severity"), issue.get("reason")),
                    )

        conn.commit()
        return scan_id


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


def get_latest_scan_summary() -> Optional[Dict[str, Any]]:
    """Return latest normalized scan summary for tests/dashboard checks."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT id, repo_path, commit_hash, status, total_issues,
                   high_count, medium_count, low_count, report_timestamp, created_at
            FROM scans
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
        return dict(row) if row else None


def get_docs_for_scan(scan_id: int) -> List[Dict[str, Any]]:
    """Return docs that were flagged for update for a scan."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT doc_file_path, severity, reason, created_at
            FROM docs_to_update
            WHERE scan_id = ?
            ORDER BY id ASC
            """,
            (scan_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_issues_for_scan(scan_id: int) -> List[Dict[str, Any]]:
    """Return normalized issues for a scan."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT reason, severity, code_element_name, code_file_path,
                   doc_file_path, message, suggestion, created_at
            FROM issues
            WHERE scan_id = ?
            ORDER BY id ASC
            """,
            (scan_id,),
        ).fetchall()
        return [dict(r) for r in rows]
