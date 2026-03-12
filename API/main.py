# API/main.py
"""
Docrot Detector — FastAPI backend.

Reads/writes JSON files in API/data/ as a lightweight datastore.
Implements the endpoints from docs/API_Contract.md.
Swap the JSON helpers for real DB calls later without changing routes.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="Docrot Detector API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173")],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# JSON file helpers (will be replaced with a real DB later)
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).resolve().parent / "data"
PROJECT_ROOT = Path(__file__).resolve().parent.parent  # repo root for scanner files


def _read_json(filename: str) -> Any:
    path = DATA_DIR / filename
    if not path.exists():
        return [] if filename.endswith("s.json") else {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(filename: str, data: Any) -> None:
    path = DATA_DIR / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ---------------------------------------------------------------------------
# Request bodies (Pydantic models)
# ---------------------------------------------------------------------------

class CreateScanBody(BaseModel):
    repo_path: str
    config_path: str = ""
    commit_sha: str = ""


class UpdateConfigBody(BaseModel):
    version: int | None = None
    language: str | None = None
    docs: dict | None = None
    code: dict | None = None
    references: dict | None = None
    hash_store: dict | None = None
    output: dict | None = None


class UpdateHashesBody(BaseModel):
    scan_id: str


# ═══════════════════════════════════════════════════════════════════════════
# SCANS
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/scans")
def list_scans():
    """Return all scans."""
    scans = _read_json("scans.json")
    return {"scans": scans}


@app.get("/scans/{scan_id}")
def get_scan(scan_id: str):
    """Return a single scan by id."""
    scans = _read_json("scans.json")
    for s in scans:
        if s["id"] == scan_id:
            return s
    raise HTTPException(status_code=404, detail="Scan does not exist")


@app.post("/scans")
def create_scan(body: CreateScanBody):
    """Create a new scan record (status='queued')."""
    scans = _read_json("scans.json")
    now = datetime.now(timezone.utc).isoformat()
    new_scan = {
        "id": f"scan-{uuid.uuid4().hex[:8]}",
        "repo_path": body.repo_path,
        "commit_sha": body.commit_sha,
        "status": "queued",
        "rot_score": 0.0,
        "mismatch_count": 0,
        "created_at": now,
        "updated_at": now,
    }
    scans.append(new_scan)
    _write_json("scans.json", scans)
    return new_scan


@app.delete("/scans/{scan_id}", status_code=204)
def delete_scan(scan_id: str):
    """Delete a scan record."""
    scans = _read_json("scans.json")
    filtered = [s for s in scans if s["id"] != scan_id]
    if len(filtered) == len(scans):
        raise HTTPException(status_code=404, detail="Scan does not exist")
    _write_json("scans.json", filtered)


# ═══════════════════════════════════════════════════════════════════════════
# REPORTS
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/scans/{scan_id}/report")
def get_report(scan_id: str):
    """Return the full report for a completed scan."""
    # Make sure the scan exists
    scans = _read_json("scans.json")
    scan = next((s for s in scans if s["id"] == scan_id), None)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan does not exist")
    if scan.get("status") != "completed":
        raise HTTPException(status_code=409, detail="Scan not completed yet")

    reports = _read_json("reports.json")
    report = reports.get(scan_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Scan does not exist")
    return report


# ═══════════════════════════════════════════════════════════════════════════
# MISMATCHES
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/scans/{scan_id}/mismatches")
def get_mismatches(scan_id: str):
    """Return all mismatches for a given scan."""
    reports = _read_json("reports.json")
    report = reports.get(scan_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Scan does not exist")
    return {"mismatches": report.get("mismatches", [])}


# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

CONFIG_PATH = PROJECT_ROOT / ".docrot-config.json"


def _read_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_config(data: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


@app.get("/config")
def get_config():
    """Return the active configuration (reads .docrot-config.json from repo root)."""
    return _read_config()


@app.put("/config")
def update_config(body: UpdateConfigBody):
    """Update configuration (partial update — only supplied fields change)."""
    config = _read_config()
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="Invalid configuration format")
    config.update(updates)
    _write_config(config)
    return config


# ═══════════════════════════════════════════════════════════════════════════
# HASHES
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/hashes")
def get_hashes():
    """Return stored baseline hashes."""
    hashes = _read_json("hashes.json")
    return {"hashes": hashes}


@app.post("/hashes/update")
def update_hashes(body: UpdateHashesBody):
    """
    Update the baseline hash store from a completed scan's report.
    Copies the code hashes from that scan's mismatches into hashes.json.
    """
    reports = _read_json("reports.json")
    report = reports.get(body.scan_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Scan does not exist")

    new_hashes = []
    for m in report.get("mismatches", []):
        code = m.get("code", {})
        new_hashes.append({
            "file": code.get("path", ""),
            "symbol": code.get("symbol", ""),
            "hash": code.get("current_hash", ""),
            "start_line": 0,
            "end_line": 0,
        })

    _write_json("hashes.json", new_hashes)
    return {"status": "ok", "count": len(new_hashes)}