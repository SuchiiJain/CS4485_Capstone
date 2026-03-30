"""
action_entrypoint.py — GitHub Actions entry point for Docrot Detector.

Runs the scan pipeline and optionally creates/updates a GitHub issue
with the results. Uses the GITHUB_TOKEN provided automatically by
GitHub Actions (no PATs or collaborator access needed).
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

SUPABASE_URL = "https://eqpnmxqzgxiedwywwmlt.supabase.co"
SUPABASE_ANON_KEY = "sb_publishable_tcalfMrQ1BhCAojEvcKH9g_g7H5IfZs"


def _supabase_headers() -> dict:
    return {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }


def _save_to_supabase(repo: str, sha: str, report_json: dict) -> None:
    """Save scan results to Supabase via its REST API."""
    scan_id = str(uuid.uuid4())
    meta = report_json.get("meta", {})
    severity = meta.get("severity_summary", {})

    scan_row = {
        "id": scan_id,
        "repo_name": repo,
        "commit_hash": sha,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "total_issues": meta.get("total_issues", 0),
        "high_count": severity.get("high", 0),
        "medium_count": severity.get("medium", 0),
        "low_count": severity.get("low", 0),
    }

    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/scan_runs",
        json=scan_row,
        headers=_supabase_headers(),
        timeout=15,
    )
    resp.raise_for_status()

    flags = []
    for issue in report_json.get("issues", []):
        flags.append({
            "id": str(uuid.uuid4()),
            "scan_id": scan_id,
            "reason": issue["reason"],
            "severity": issue["severity"],
            "file_path": issue["code_element"]["file_path"],
            "symbol": issue["code_element"]["name"],
            "message": issue["message"],
            "suggestion": issue.get("suggestion"),
        })

    if flags:
        resp = requests.post(
            f"{SUPABASE_URL}/rest/v1/flags",
            json=flags,
            headers=_supabase_headers(),
            timeout=15,
        )
        resp.raise_for_status()


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
    # 422 = label already exists — that's fine
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


def main() -> None:
    repo_path = os.environ.get("INPUT_REPO_PATH", ".")
    create_issue = os.environ.get("INPUT_CREATE_ISSUE", "true").lower() == "true"
    repo = os.environ["GITHUB_REPOSITORY"]
    sha = os.environ.get("GITHUB_SHA", "unknown")

    # Run the pipeline
    exit_code = run_pipeline(repo_path, commit_hash=sha)

    # Save scan to database
    report_path = os.path.join(os.path.abspath(repo_path), ".docrot-report.json")
    try:
        if os.path.exists(report_path):
            with open(report_path, "r", encoding="utf-8") as f:
                report_json = json.load(f)
            _save_to_supabase(repo, sha, report_json)
            print(f"[docrot-action] Scan saved to database for {repo}")
    except Exception as e:
        print(f"[docrot-action] Warning: could not save to database: {e}")

    if not create_issue:
        # When issue creation is disabled, use exit code to signal CI
        sys.exit(exit_code)

    existing_issue = _find_existing_issue(repo)

    if exit_code == 1:
        # Alerts found — create or update the issue
        body = format_pr_comment(report_path, sha)
        if not body:
            body = f"Docrot Detector found documentation issues at commit `{sha[:8]}`. See the action logs for details."

        if existing_issue:
            _update_issue(repo, existing_issue, body)
        else:
            _create_issue(repo, body)
    elif exit_code == 0 and existing_issue:
        # Clean scan — close the outstanding issue
        _close_issue(repo, existing_issue)

    # Always exit 0 — the Action succeeded; alerts are communicated via issues.
    # Exit code 2 (error) still propagates as a real failure.
    sys.exit(0 if exit_code in (0, 1) else exit_code)


if __name__ == "__main__":
    main()
