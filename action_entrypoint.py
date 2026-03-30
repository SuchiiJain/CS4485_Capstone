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


def _load_baseline(repo: str, branch: str, repo_path: str) -> None:
    """Download the fingerprint baseline from Supabase and write it to the repo."""
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/fingerprint_baselines",
        params={
            "repo_name": f"eq.{repo}",
            "branch": f"eq.{branch}",
            "select": "fingerprints",
            "limit": "1",
        },
        headers=_supabase_headers(),
        timeout=15,
    )
    resp.raise_for_status()
    rows = resp.json()
    if rows:
        fp_path = os.path.join(repo_path, ".docrot-fingerprints.json")
        with open(fp_path, "w", encoding="utf-8") as f:
            json.dump(rows[0]["fingerprints"], f, indent=2, sort_keys=True)
        print(f"[docrot-action] Loaded fingerprint baseline from database.")


def _save_baseline(repo: str, branch: str, repo_path: str) -> None:
    """Upload the updated fingerprint baseline to Supabase."""
    fp_path = os.path.join(repo_path, ".docrot-fingerprints.json")
    if not os.path.exists(fp_path):
        return
    with open(fp_path, "r", encoding="utf-8") as f:
        fingerprints = json.load(f)
    headers = {**_supabase_headers(), "Prefer": "return=minimal,resolution=merge-duplicates"}
    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/fingerprint_baselines?on_conflict=repo_name,branch",
        json={
            "repo_name": repo,
            "branch": branch,
            "fingerprints": fingerprints,
        },
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    print(f"[docrot-action] Fingerprint baseline saved to database.")


def _save_to_supabase(repo: str, sha: str, branch: str, status: str, report_json: dict) -> None:
    """Save scan results to Supabase via its REST API."""
    scan_id = str(uuid.uuid4())
    meta = report_json.get("meta", {})
    severity = meta.get("severity_summary", {})
    headers = _supabase_headers()

    # 1. Insert scan run
    scan_row = {
        "id": scan_id,
        "repo_name": repo,
        "commit_hash": sha,
        "branch": branch,
        "status": status,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "total_issues": meta.get("total_issues", 0),
        "high_count": severity.get("high", 0),
        "medium_count": severity.get("medium", 0),
        "low_count": severity.get("low", 0),
    }

    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/scan_runs",
        json=scan_row,
        headers=headers,
        timeout=15,
    )
    resp.raise_for_status()

    # 2. Insert flags with full detail
    flags = []
    for issue in report_json.get("issues", []):
        code_el = issue.get("code_element", {})
        doc_ref = issue.get("doc_reference")
        flags.append({
            "id": str(uuid.uuid4()),
            "scan_id": scan_id,
            "reason": issue["reason"],
            "severity": issue["severity"],
            "file_path": code_el.get("file_path"),
            "symbol": code_el.get("name"),
            "message": issue["message"],
            "suggestion": issue.get("suggestion"),
            "signature": code_el.get("signature"),
            "params": json.dumps(code_el.get("params", [])),
            "return_type": code_el.get("return_type"),
            "doc_file": doc_ref["file_path"] if doc_ref else None,
            "doc_symbol": doc_ref["referenced_symbol"] if doc_ref else None,
        })

    if flags:
        resp = requests.post(
            f"{SUPABASE_URL}/rest/v1/flags",
            json=flags,
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()

    # 3. Upsert repo (create on first scan, update latest_scan_id on subsequent)
    repo_row = {
        "full_name": repo,
        "github_url": f"https://github.com/{repo}",
        "latest_scan_id": scan_id,
    }
    upsert_headers = {**headers, "Prefer": "return=minimal,resolution=merge-duplicates"}
    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/repos?on_conflict=full_name",
        json=repo_row,
        headers=upsert_headers,
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
    branch = os.environ.get("GITHUB_REF_NAME", "unknown")

    # Load fingerprint baseline from database (if one exists)
    try:
        _load_baseline(repo, branch, os.path.abspath(repo_path))
    except Exception as e:
        print(f"[docrot-action] Warning: could not load baseline from database: {e}")

    # Run the pipeline
    exit_code = run_pipeline(repo_path, commit_hash=sha)

    # Save scan results and updated baseline to database
    report_path = os.path.join(os.path.abspath(repo_path), ".docrot-report.json")
    status = "issues_found" if exit_code == 1 else "clean"
    try:
        if os.path.exists(report_path):
            with open(report_path, "r", encoding="utf-8") as f:
                report_json = json.load(f)
            _save_to_supabase(repo, sha, branch, status, report_json)
            print(f"[docrot-action] Scan saved to database for {repo}")
        _save_baseline(repo, branch, os.path.abspath(repo_path))
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
