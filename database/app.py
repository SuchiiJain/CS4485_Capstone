import os
from typing import Any, Dict, Optional

from flask import Flask, request, jsonify
from database.storage import (
    get_repo_summary,
    get_scan,
    get_scan_issues,
    init_db,
    list_scans,
    save_scan,
)

app = Flask(__name__)

_db_initialized = False


def _ensure_db_initialized() -> bool:
    global _db_initialized
    if _db_initialized:
        return True

    try:
        init_db()
        _db_initialized = True
        return True
    except Exception as exc:
        print(f"[database] init failed: {exc}")
        return False


def _normalize_int(raw: Optional[str], default_value: int, minimum: int, maximum: int) -> int:
    if raw is None:
        return default_value
    try:
        val = int(raw)
    except ValueError:
        return default_value
    return max(minimum, min(maximum, val))


def _register_not_implemented(route: str, methods: list[str], response_body: Dict[str, Any]) -> None:
    route_part = route.strip("/").replace("/", "_").replace("<", "").replace(">", "") or "root_placeholder"
    method_part = "_".join(sorted(m.lower() for m in methods))
    endpoint_name = f"placeholder_{route_part}_{method_part}"

    def handler(**_: Any):
        body = dict(response_body)
        body["implemented"] = False
        body["message"] = "Endpoint contract is reserved and will be connected by auth/config teams."
        return jsonify(body), 501

    app.add_url_rule(route, endpoint_name, handler, methods=methods)


@app.route("/")
def root():
    return {"service": "docrot-backend", "status": "ok"}


@app.route("/health")
def health():
    return {"status": "ok"}


@app.route("/api/scan", methods=["POST"])
def receive_scan():
    if not _ensure_db_initialized():
        return jsonify({"error": "Database unavailable"}), 503

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Body must be a JSON object"}), 400

    repo = data.get("repo")
    commit = data.get("commit")
    report = data.get("report")

    if not repo or not commit or not isinstance(report, dict):
        return jsonify({"error": "Missing required fields: repo, commit, report"}), 400

    scan_id = save_scan(repo, commit, report)

    return jsonify({"message": "Scan stored", "scan_id": scan_id}), 200


@app.route("/api/scans", methods=["GET"])
def api_scans():
    if not _ensure_db_initialized():
        return jsonify({"error": "Database unavailable"}), 503

    repo = request.args.get("repo")
    limit = _normalize_int(request.args.get("limit"), default_value=25, minimum=1, maximum=100)
    offset = _normalize_int(request.args.get("offset"), default_value=0, minimum=0, maximum=100000)

    items, total = list_scans(repo_name=repo, limit=limit, offset=offset)
    return jsonify({"items": items, "total": total, "limit": limit, "offset": offset}), 200


@app.route("/api/scans/<scan_id>", methods=["GET"])
def api_scan_detail(scan_id: str):
    if not _ensure_db_initialized():
        return jsonify({"error": "Database unavailable"}), 503

    record = get_scan(scan_id)
    if not record:
        return jsonify({"error": "Scan not found"}), 404

    return jsonify(record), 200


@app.route("/api/scans/<scan_id>/issues", methods=["GET"])
def api_scan_issues(scan_id: str):
    if not _ensure_db_initialized():
        return jsonify({"error": "Database unavailable"}), 503

    severity = request.args.get("severity")
    if severity:
        severity = severity.lower().strip()
        if severity not in {"high", "medium", "low"}:
            return jsonify({"error": "severity must be one of: high, medium, low"}), 400

    limit = _normalize_int(request.args.get("limit"), default_value=50, minimum=1, maximum=200)
    offset = _normalize_int(request.args.get("offset"), default_value=0, minimum=0, maximum=100000)

    items, total = get_scan_issues(scan_id=scan_id, severity=severity, limit=limit, offset=offset)
    return jsonify({"items": items, "total": total, "limit": limit, "offset": offset}), 200


@app.route("/api/repos/<path:repo>/summary", methods=["GET"])
def api_repo_summary(repo: str):
    if not _ensure_db_initialized():
        return jsonify({"error": "Database unavailable"}), 503

    return jsonify(get_repo_summary(repo)), 200


@app.route("/auth/providers/github/start", methods=["GET"])
def auth_provider_start():
    # Placeholder route to reserve contract for Supabase OAuth handoff.
    return jsonify({
        "implemented": False,
        "message": "Supabase OAuth start route will be provided by auth team.",
    }), 501


@app.route("/auth/providers/github/callback", methods=["GET"])
def auth_provider_callback():
    return jsonify({
        "implemented": False,
        "message": "Supabase OAuth callback route will be provided by auth team.",
    }), 501


_register_not_implemented("/auth/login", ["POST"], {"access_token": None, "refresh_token": None, "user": None})
_register_not_implemented("/auth/register", ["POST"], {"user": None})
_register_not_implemented("/auth/logout", ["POST"], {"ok": False})
_register_not_implemented("/auth/refresh", ["POST"], {"access_token": None, "refresh_token": None})
_register_not_implemented("/auth/me", ["GET"], {"user": None})

_register_not_implemented("/api/projects", ["GET"], {"projects": [], "total": 0})
_register_not_implemented("/api/projects", ["POST"], {"project": None})
_register_not_implemented("/api/projects/<project_id>", ["GET"], {"project": None})
_register_not_implemented("/api/projects/<project_id>", ["PUT"], {"project": None})
_register_not_implemented("/api/projects/<project_id>", ["DELETE"], {"ok": False})
_register_not_implemented("/api/projects/<project_id>/scans", ["GET"], {"items": [], "total": 0})

_register_not_implemented("/api/config/mappings", ["GET"], {"items": []})
_register_not_implemented("/api/config/mappings", ["POST"], {"mapping": None})
_register_not_implemented("/api/config/mappings/<mapping_id>", ["PUT"], {"mapping": None})
_register_not_implemented("/api/config/mappings/<mapping_id>", ["DELETE"], {"ok": False})
_register_not_implemented("/api/config/detection", ["GET"], {"detection": None})
_register_not_implemented("/api/config/detection", ["PUT"], {"detection": None})
_register_not_implemented("/api/config/alerts", ["GET"], {"alerts": None})
_register_not_implemented("/api/config/alerts", ["PUT"], {"alerts": None})

_register_not_implemented("/api/user/profile", ["GET"], {"profile": None})
_register_not_implemented("/api/user/profile", ["PATCH"], {"profile": None})
_register_not_implemented("/api/user/password", ["PATCH"], {"ok": False})
_register_not_implemented("/api/user/security", ["GET"], {"security": None})
_register_not_implemented("/api/user/security/2fa/enable", ["POST"], {"ok": False})
_register_not_implemented("/api/user/security/2fa/disable", ["POST"], {"ok": False})
_register_not_implemented("/api/user/notifications", ["GET"], {"notifications": None})
_register_not_implemented("/api/user/notifications", ["PATCH"], {"notifications": None})
_register_not_implemented("/api/user/tokens", ["GET"], {"items": []})
_register_not_implemented("/api/user/tokens", ["POST"], {"token": None})
_register_not_implemented("/api/user/tokens/<token_id>", ["DELETE"], {"ok": False})

_register_not_implemented("/api/reports", ["GET"], {"items": [], "total": 0})
_register_not_implemented("/api/reports/<report_id>", ["GET"], {"report": None})
_register_not_implemented("/api/reports/export", ["POST"], {"job_id": None})
_register_not_implemented("/api/scans/<scan_id>/report", ["GET"], {"report": None})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
