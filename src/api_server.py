"""
api_server.py -- lightweight read API for dashboard/frontend integration.

Usage:
    python -m src.api_server

Environment variables:
    DOCROT_API_HOST      Host bind address (default: 127.0.0.1)
    DOCROT_API_PORT      Port (default: 8000)
    DOCROT_API_TOKEN     Optional bearer token for /api routes
    DOCROT_DB_PATH       Optional path override for SQLite database file
"""

import json
import os
import time
from typing import Any, Dict

from flask import Flask, Response, jsonify, request, stream_with_context

from database.storage import (
    get_docs_for_scan,
    get_latest_scan_summary,
    get_fingerprint_count,
    get_report_for_scan,
    get_scan_by_id,
    get_issues_for_scan,
    init_db,
    list_scans,
)


app = Flask(__name__)
API_TOKEN = os.environ.get("DOCROT_API_TOKEN", "")


def _json_error(message: str, status: int):
    return jsonify({"error": message}), status


def _auth_ok() -> bool:
    if not API_TOKEN:
        return True

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        # EventSource cannot set custom headers in browsers.
        # Allow token in query string for SSE routes only.
        if request.path.startswith("/api/events/"):
            return request.args.get("token", "") == API_TOKEN
        return False

    token = auth_header.removeprefix("Bearer ").strip()
    return token == API_TOKEN


@app.before_request
def _protect_api_routes():
    if request.path == "/api/health":
        return None

    if request.path.startswith("/api/") and not _auth_ok():
        return _json_error("Unauthorized", 401)


@app.after_request
def _add_cors_headers(response):
    # Keep simple for cross-repo frontend development.
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    return response


@app.route("/api/health", methods=["GET", "OPTIONS"])
def health():
    if request.method == "OPTIONS":
        return ("", 204)
    return jsonify({"status": "ok"})


@app.route("/api/scans", methods=["GET", "OPTIONS"])
def api_list_scans():
    if request.method == "OPTIONS":
        return ("", 204)

    try:
        limit = int(request.args.get("limit", "50"))
        offset = int(request.args.get("offset", "0"))
    except ValueError:
        return _json_error("Invalid limit/offset", 400)

    limit = max(1, min(limit, 500))
    offset = max(0, offset)

    scans = list_scans(limit=limit, offset=offset)
    return jsonify({"scans": scans, "limit": limit, "offset": offset})


@app.route("/api/scans/<int:scan_id>", methods=["GET", "OPTIONS"])
def api_get_scan(scan_id: int):
    if request.method == "OPTIONS":
        return ("", 204)

    scan = get_scan_by_id(scan_id)
    if not scan:
        return _json_error("Scan not found", 404)
    return jsonify({"scan": scan})


@app.route("/api/scans/<int:scan_id>/issues", methods=["GET", "OPTIONS"])
def api_scan_issues(scan_id: int):
    if request.method == "OPTIONS":
        return ("", 204)

    if not get_scan_by_id(scan_id):
        return _json_error("Scan not found", 404)

    issues = get_issues_for_scan(scan_id)
    return jsonify({"scan_id": scan_id, "issues": issues})


@app.route("/api/scans/<int:scan_id>/docs", methods=["GET", "OPTIONS"])
def api_scan_docs(scan_id: int):
    if request.method == "OPTIONS":
        return ("", 204)

    if not get_scan_by_id(scan_id):
        return _json_error("Scan not found", 404)

    docs = get_docs_for_scan(scan_id)
    return jsonify({"scan_id": scan_id, "docs": docs})


@app.route("/api/scans/<int:scan_id>/report", methods=["GET", "OPTIONS"])
def api_scan_report(scan_id: int):
    if request.method == "OPTIONS":
        return ("", 204)

    if not get_scan_by_id(scan_id):
        return _json_error("Scan not found", 404)

    row = get_report_for_scan(scan_id, fmt="json")
    if not row:
        return _json_error("Report not found", 404)

    content = row.get("content", "{}")
    try:
        payload: Dict[str, Any] = json.loads(content)
    except json.JSONDecodeError:
        payload = {"raw": content}

    return jsonify({"scan_id": scan_id, "report": payload})


@app.route("/api/fingerprints/summary", methods=["GET", "OPTIONS"])
def api_fingerprint_summary():
    if request.method == "OPTIONS":
        return ("", 204)

    return jsonify({"fingerprint_count": get_fingerprint_count()})


@app.route("/api/events/scans", methods=["GET"])
def api_scan_events():
    """
    Server-Sent Events stream that emits when a new scan row appears.

    Query params:
        token   Optional auth token when using browser EventSource.
        last_id Optional integer scan id already seen by the client.
    """
    try:
        last_seen = int(request.args.get("last_id", "0"))
    except ValueError:
        return _json_error("Invalid last_id", 400)

    poll_seconds = float(os.environ.get("DOCROT_EVENTS_POLL_SECONDS", "2"))
    poll_seconds = max(0.5, poll_seconds)

    @stream_with_context
    def event_stream():
        nonlocal last_seen

        # Initial event confirms stream connection.
        yield 'event: connected\ndata: {"status":"connected"}\n\n'

        while True:
            latest = get_latest_scan_summary()
            if latest and int(latest.get("id", 0)) > last_seen:
                last_seen = int(latest["id"])
                payload = {
                    "scan_id": latest["id"],
                    "commit_hash": latest.get("commit_hash"),
                    "status": latest.get("status"),
                    "total_issues": latest.get("total_issues", 0),
                    "created_at": latest.get("created_at"),
                }
                yield f"event: scan_added\\ndata: {json.dumps(payload)}\\n\\n"
            else:
                # Keep connection alive for intermediaries/timeouts.
                yield ": keepalive\n\n"

            time.sleep(poll_seconds)

    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
    }
    return Response(event_stream(), headers=headers)


def main() -> None:
    init_db()
    host = os.environ.get("DOCROT_API_HOST", "127.0.0.1")
    port = int(os.environ.get("DOCROT_API_PORT", "8000"))
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
