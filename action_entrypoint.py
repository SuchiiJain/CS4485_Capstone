"""
action_entrypoint.py — GitHub Actions entry point for Docrot Detector.

Runs the scan pipeline and optionally creates/updates a GitHub issue
with the results. Uses the GITHUB_TOKEN provided automatically by
GitHub Actions (no PATs or collaborator access needed).

Scan results are saved to Firebase Firestore.
"""

import json
import os
import sys
import uuid
from datetime import datetime, timezone

import requests

from src.run import run as run_pipeline
from src.github_integration import format_pr_comment


ISSUE_TITLE = "⚠️ Docrot Detector — Documentation may be stale"
ISSUE_LABEL = "docrot"


# ---------------------------------------------------------------------------
# Firebase / Firestore helpers
# ---------------------------------------------------------------------------

_firestore_db = None


def _get_firestore_db():
    """Lazily initialize the Firebase Admin SDK and return a Firestore client."""
    global _firestore_db
    if _firestore_db is not None:
        return _firestore_db

    import firebase_admin
    from firebase_admin import credentials, firestore

    sa_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
    if not sa_json:
        raise RuntimeError("FIREBASE_SERVICE_ACCOUNT environment variable is not set.")

    sa_dict = json.loads(sa_json)
    cred = credentials.Certificate(sa_dict)
    firebase_admin.initialize_app(cred)
    _firestore_db = firestore.client()
    return _firestore_db


def _repo_doc_id(repo: str) -> str:
    """Convert 'owner/repo-name' to 'owner_repo-name' for the Firestore document ID."""
    return repo.replace("/", "_")


def _load_baseline(repo: str, branch: str, repo_path: str) -> None:
    """Download the fingerprint baseline from Firestore and write it to the repo."""
    db = _get_firestore_db()
    repo_id = _repo_doc_id(repo)
    baselines_ref = db.collection("repos").document(repo_id).collection("fingerprint_baselines")
    docs = baselines_ref.where("branch", "==", branch).limit(1).get()

    for doc in docs:
        data = doc.to_dict()
        fingerprints = data.get("fingerprints")
        if fingerprints:
            fp_path = os.path.join(repo_path, ".docrot-fingerprints.json")
            with open(fp_path, "w", encoding="utf-8") as f:
                json.dump(fingerprints, f, indent=2, sort_keys=True)
            print("[docrot-action] Loaded fingerprint baseline from Firestore.")
            return

    print("[docrot-action] No existing baseline found in Firestore.")


def _save_baseline(repo: str, branch: str, repo_path: str) -> None:
    """Upload the updated fingerprint baseline to Firestore."""
    fp_path = os.path.join(repo_path, ".docrot-fingerprints.json")
    if not os.path.exists(fp_path):
        return
    with open(fp_path, "r", encoding="utf-8") as f:
        fingerprints = json.load(f)

    db = _get_firestore_db()
    repo_id = _repo_doc_id(repo)
    baseline_ref = (
        db.collection("repos")
        .document(repo_id)
        .collection("fingerprint_baselines")
        .document(branch)
    )
    baseline_ref.set(
        {"branch": branch, "fingerprints": fingerprints, "updated_at": datetime.now(timezone.utc)},
        merge=True,
    )
    print("[docrot-action] Fingerprint baseline saved to Firestore.")


def _compute_rot_score(high: int, medium: int, low: int) -> int:
    """Compute a documentation health score (0-100). 100 = perfectly healthy."""
    penalty = high * 15 + medium * 8 + low * 3
    return max(0, 100 - penalty)


def _save_to_firestore(repo: str, sha: str, branch: str, status: str, report_json: dict) -> None:
    """Save scan results to Firestore."""
    db = _get_firestore_db()
    scan_id = str(uuid.uuid4())
    meta = report_json.get("meta", {})
    severity = meta.get("severity_summary", {})
    repo_id = _repo_doc_id(repo)
    now = datetime.now(timezone.utc)

    high = severity.get("high", 0)
    medium = severity.get("medium", 0)
    low = severity.get("low", 0)

    # 1. Write scan run document
    scan_data = {
        "commit_hash": sha,
        "branch": branch,
        "status": status,
        "scanned_at": now,
        "total_issues": meta.get("total_issues", 0),
        "high_count": high,
        "medium_count": medium,
        "low_count": low,
        "rot_score": _compute_rot_score(high, medium, low),
    }
    db.collection("repos").document(repo_id).collection("scan_runs").document(scan_id).set(scan_data)

    # 2. Write individual issues as sub-documents
    issues = report_json.get("issues", [])
    for issue in issues:
        code_el = issue.get("code_element", {})
        doc_ref = issue.get("doc_reference")
        issue_id = str(uuid.uuid4())
        issue_data = {
            "reason": issue.get("reason", ""),
            "severity": issue.get("severity", "low"),
            "file_path": code_el.get("file_path"),
            "symbol": code_el.get("name"),
            "message": issue.get("message", ""),
            "suggestion": issue.get("suggestion"),
            "signature": code_el.get("signature"),
            "params": code_el.get("params", []),
            "return_type": code_el.get("return_type"),
            "doc_file": doc_ref["file_path"] if doc_ref else None,
            "doc_symbol": doc_ref["referenced_symbol"] if doc_ref else None,
        }
        (
            db.collection("repos")
            .document(repo_id)
            .collection("scan_runs")
            .document(scan_id)
            .collection("issues")
            .document(issue_id)
            .set(issue_data)
        )

    # 3. Upsert repo document
    repo_ref = db.collection("repos").document(repo_id)
    repo_ref.set(
        {
            "full_name": repo,
            "github_url": f"https://github.com/{repo}",
            "latest_scan_id": scan_id,
            "first_seen_at": now,
        },
        merge=True,
    )

    print(f"[docrot-action] Scan {scan_id} saved to Firestore for {repo}")


# ---------------------------------------------------------------------------
# GitHub helpers (unchanged)
# ---------------------------------------------------------------------------

def _gh_headers() -> dict:
    token = os.environ["GITHUB_TOKEN"]
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _find_existing_issue(repo: str) -> int | None:
    """Find an open issue with the docrot label, return its number or None."""
    url = f"https://api.github.com/repos/{repo}/issues"
    params = {"labels": ISSUE_LABEL, "state": "open", "per_page": 1}
    resp = requests.get(url, headers=_gh_headers(), params=params, timeout=15)
    if resp.status_code == 200 and resp.json():
        return resp.json()[0]["number"]
    return None


def _ensure_label(repo: str) -> None:
    """Create the 'docrot' label if it doesn't exist."""
    url = f"https://api.github.com/repos/{repo}/labels"
    payload = {
        "name": ISSUE_LABEL,
        "color": "FBCA04",
        "description": "Documentation rot detected by Docrot Detector",
    }
    resp = requests.post(url, json=payload, headers=_gh_headers(), timeout=15)
    if resp.status_code == 201:
        print(f"[docrot-action] Created '{ISSUE_LABEL}' label.")
    elif resp.status_code != 422:
        print(f"[docrot-action] Warning: could not create label: {resp.status_code}")


def _create_issue(repo: str, body: str) -> None:
    """Create a new issue."""
    _ensure_label(repo)
    url = f"https://api.github.com/repos/{repo}/issues"
    payload = {
        "title": ISSUE_TITLE,
        "body": body,
        "labels": [ISSUE_LABEL],
    }
    resp = requests.post(url, json=payload, headers=_gh_headers(), timeout=15)
    if resp.status_code == 201:
        print(f"[docrot-action] Issue created: {resp.json()['html_url']}")
    else:
        print(f"[docrot-action] Failed to create issue: {resp.status_code} {resp.text[:200]}")


def _update_issue(repo: str, issue_number: int, body: str) -> None:
    """Update an existing issue's body."""
    url = f"https://api.github.com/repos/{repo}/issues/{issue_number}"
    payload = {"body": body}
    resp = requests.patch(url, json=payload, headers=_gh_headers(), timeout=15)
    if resp.status_code == 200:
        print(f"[docrot-action] Issue #{issue_number} updated.")
    else:
        print(f"[docrot-action] Failed to update issue: {resp.status_code} {resp.text[:200]}")


def _close_issue(repo: str, issue_number: int) -> None:
    """Close an existing issue (scan is now clean)."""
    url = f"https://api.github.com/repos/{repo}/issues/{issue_number}"
    payload = {"state": "closed", "state_reason": "completed"}
    resp = requests.patch(url, json=payload, headers=_gh_headers(), timeout=15)
    if resp.status_code == 200:
        print(f"[docrot-action] Issue #{issue_number} closed (scan clean).")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    repo_path = os.environ.get("INPUT_REPO_PATH", ".")
    create_issue = os.environ.get("INPUT_CREATE_ISSUE", "true").lower() == "true"
    repo = os.environ["GITHUB_REPOSITORY"]
    sha = os.environ.get("GITHUB_SHA", "unknown")
    branch = os.environ.get("GITHUB_REF_NAME", "unknown")

    # Load fingerprint baseline from Firestore (if one exists)
    try:
        _load_baseline(repo, branch, os.path.abspath(repo_path))
    except Exception as e:
        print(f"[docrot-action] Warning: could not load baseline from Firestore: {e}")

    # Run the pipeline
    exit_code = run_pipeline(repo_path, commit_hash=sha)

    # Save scan results and updated baseline to Firestore
    report_path = os.path.join(os.path.abspath(repo_path), ".docrot-report.json")
    status = "issues_found" if exit_code == 1 else "clean"
    try:
        if os.path.exists(report_path):
            with open(report_path, "r", encoding="utf-8") as f:
                report_json = json.load(f)
            _save_to_firestore(repo, sha, branch, status, report_json)
            print(f"[docrot-action] Scan saved to Firestore for {repo}")
        _save_baseline(repo, branch, os.path.abspath(repo_path))
    except Exception as e:
        print(f"[docrot-action] Warning: could not save to Firestore: {e}")

    if not create_issue:
        sys.exit(exit_code)

    existing_issue = _find_existing_issue(repo)

    if exit_code == 1:
        body = format_pr_comment(report_path, sha)
        if not body:
            body = f"Docrot Detector found documentation issues at commit `{sha[:8]}`. See the action logs for details."

        if existing_issue:
            _update_issue(repo, existing_issue, body)
        else:
            _create_issue(repo, body)
    elif exit_code == 0 and existing_issue:
        _close_issue(repo, existing_issue)

    sys.exit(0 if exit_code in (0, 1) else exit_code)


if __name__ == "__main__":
    main()
