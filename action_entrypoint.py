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

BACKEND_URL = os.environ.get("DOCROT_BACKEND_URL", "").rstrip("/")
BACKEND_TOKEN = os.environ.get("DOCROT_BACKEND_TOKEN", "")

# ---------------------------------------------------------------------------
# Firebase / Firestore helpers
# ---------------------------------------------------------------------------

def _backend_headers() -> dict:
    headers = {"Content-Type": "application/json"}
    if BACKEND_TOKEN:
        headers["Authorization"] = f"Bearer {BACKEND_TOKEN}"
    return headers


def _load_baseline(repo: str, branch: str, repo_path: str) -> None:
    """Download the fingerprint baseline from Firestore and write it to the repo."""
    if not BACKEND_URL:
        return

    resp = requests.get(
        BACKEND_URL,
        params={"repo": repo, "branch": branch},
        headers=_backend_headers(),
        timeout=15,
    )

    if resp.status_code == 404:
        print("[docrot-action] No existing baseline found — this will be a first run.")
        return

    resp.raise_for_status()
    data = resp.json()

    if data.get("fingerprints"):
        fp_path = os.path.join(repo_path, ".docrot-fingerprints.json")
        with open(fp_path, "w", encoding="utf-8") as f:
            json.dump(data["fingerprints"], f, indent=2, sort_keys=True)
        print("[docrot-action] Loaded fingerprint baseline from database.")


def _save_to_backend(repo: str, sha: str, branch: str, status: str, report_json: dict, repo_path: str) -> list:
    """Send scan payload to the Cloud Function backend endpoint.

    Returns a list of AI suggestion dicts from the backend response,
    or an empty list if AI is not available or the call fails.
    """
    if not BACKEND_URL:
        return []

    scan_id = str(uuid.uuid4())
    meta = report_json.get("meta", {})
    severity = meta.get("severity_summary", {})

    flags = []
    for issue in report_json.get("issues", []):
        code_el = issue.get("code_element", {})
        doc_ref = issue.get("doc_reference")
        flags.append({
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
        })

    fingerprints = None
    fp_path = os.path.join(repo_path, ".docrot-fingerprints.json")
    if os.path.exists(fp_path):
        with open(fp_path, "r", encoding="utf-8") as f:
            fingerprints = json.load(f)

    payload = {
        "repo_name": repo,
        "github_url": f"https://github.com/{repo}",
        "scan_id": scan_id,
        "commit_hash": sha,
        "branch": branch,
        "status": status,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "total_issues": meta.get("total_issues", 0),
        "high_count": severity.get("high", 0),
        "medium_count": severity.get("medium", 0),
        "low_count": severity.get("low", 0),
        "flags": flags,
    }
    if fingerprints is not None:
        payload["fingerprints"] = fingerprints

    # Send AI context so the backend can generate suggestions server-side
    ai_context = report_json.get("ai_context", [])
    if ai_context:
        payload["ai_context"] = ai_context

    resp = requests.post(
        BACKEND_URL,
        json=payload,
        headers=_backend_headers(),
        timeout=60,
    )

    print(f"[docrot-action] Scan {scan_id} saved to Firestore for {repo}")

    # Extract AI suggestions from the backend response
    try:
        body = resp.json()
        return body.get("ai_suggestions", [])
    except (ValueError, AttributeError):
        return []


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

    # Load fingerprint baseline from database (if one exists)
    try:
        _load_baseline(repo, branch, os.path.abspath(repo_path))
    except Exception as e:
        print(f"[docrot-action] Warning: could not load baseline from database: {e}")

    # Run the pipeline
    exit_code = run_pipeline(repo_path, commit_hash=sha)

    # Save scan results to Cloud Function backend
    report_path = os.path.join(os.path.abspath(repo_path), ".docrot-report.json")
    status = "issues_found" if exit_code == 1 else "clean"
    ai_suggestions = []
    if BACKEND_URL:
        try:
            if os.path.exists(report_path):
                with open(report_path, "r", encoding="utf-8") as f:
                    report_json = json.load(f)
                ai_suggestions = _save_to_backend(repo, sha, branch, status, report_json, os.path.abspath(repo_path))
                print(f"[docrot-action] Scan sent to Cloud Function backend for {repo}")

                # Write AI suggestions from backend into the report JSON
                # so format_pr_comment() picks them up for the GitHub issue
                if ai_suggestions:
                    report_json["ai_suggestions"] = ai_suggestions
                    with open(report_path, "w", encoding="utf-8") as f:
                        json.dump(report_json, f, indent=2)
                    print(f"[docrot-action] {len(ai_suggestions)} AI suggestion(s) added to report.")
        except Exception as e:
            print(f"[docrot-action] Warning: could not send scan to backend: {e}")

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
