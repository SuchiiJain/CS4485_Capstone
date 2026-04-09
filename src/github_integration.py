"""
GitHub Integration — Git operations and GitHub API helpers for the
Docrot Detector webhook pipeline.

Responsibilities:
    - Clone a repository (or pull latest if already cloned)
    - Checkout the correct branch / commit
    - Commit and push report files back to the repo
    - Post commit statuses to GitHub via the REST API

Dependencies:
    - git CLI must be available on PATH
    - `requests` library for GitHub API calls
"""

import os
import shutil
import subprocess
from typing import List, Optional

import requests


# ---------------------------------------------------------------------------
# GitHub API base + shared headers helper
# ---------------------------------------------------------------------------

GITHUB_API_BASE = "https://api.github.com"


def _gh_headers(token: str) -> dict:
    """Standard headers for GitHub API calls."""
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


# ---------------------------------------------------------------------------
# Git clone / pull helpers
# ---------------------------------------------------------------------------

def _authenticated_clone_url(clone_url: str, token: Optional[str] = None) -> str:
    """
    Inject a GitHub token into an HTTPS clone URL for private-repo access.

    Public repos work without a token.  For private repos the token is
    embedded as:  https://<token>@github.com/owner/repo.git

    Args:
        clone_url: Original HTTPS clone URL.
        token:     GitHub personal access token (optional).

    Returns:
        Clone URL (possibly with token embedded).
    """
    if not token:
        return clone_url

    # https://github.com/owner/repo.git → https://<token>@github.com/owner/repo.git
    if clone_url.startswith("https://"):
        return clone_url.replace("https://", f"https://{token}@", 1)

    return clone_url


def _run_git(args: list[str], cwd: Optional[str] = None) -> subprocess.CompletedProcess:
    """
    Run a git command, capturing stdout/stderr.

    Raises:
        subprocess.CalledProcessError on non-zero exit.
    """
    cmd = ["git"] + args
    # Mask tokens in log output
    safe_cmd = " ".join(cmd).replace(os.environ.get("GITHUB_TOKEN", ""), "***")
    print(f"[git] {safe_cmd}")

    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
        timeout=300,  # 5 min ceiling for large repos
    )


def clone_or_pull_repo(
    clone_url: str,
    repo_full_name: str,
    branch: str = "main",
    clone_dir: str = "./repos",
    token: Optional[str] = None,
) -> str:
    """
    Clone a repository (or pull latest if already cloned) and check out
    the specified branch.

    Repos are stored under ``<clone_dir>/<owner>/<repo>/``.

    Args:
        clone_url:      HTTPS clone URL from the webhook payload.
        repo_full_name: "owner/repo" string.
        branch:         Branch to check out.
        clone_dir:      Parent directory for all cloned repos.
        token:          Optional GitHub token for private-repo access.

    Returns:
        Absolute path to the cloned repo directory.
    """
    repo_path = os.path.join(clone_dir, repo_full_name.replace("/", os.sep))
    auth_url = _authenticated_clone_url(clone_url, token)

    if os.path.isdir(os.path.join(repo_path, ".git")):
        # Repo already cloned — fetch + checkout
        print(f"[git] Updating existing clone: {repo_path}")
        _run_git(["fetch", "--all", "--prune"], cwd=repo_path)
        _run_git(["checkout", branch], cwd=repo_path)
        _run_git(["reset", "--hard", f"origin/{branch}"], cwd=repo_path)
        _run_git(["clean", "-fdx", "--exclude=.docrot-fingerprints.json"], cwd=repo_path)
    else:
        # Fresh clone
        print(f"[git] Cloning {repo_full_name} (branch {branch}) → {repo_path}")
        os.makedirs(os.path.dirname(repo_path), exist_ok=True)
        _run_git([
            "clone",
            "--branch", branch,
            "--single-branch",
            auth_url,
            repo_path,
        ])

    return os.path.abspath(repo_path)


def checkout_commit(repo_path: str, sha: str) -> None:
    """
    Check out a specific commit (detached HEAD).

    Useful when you need to scan the exact commit that was pushed,
    rather than the branch tip.

    Args:
        repo_path: Path to the local clone.
        sha:       Full or abbreviated commit SHA.
    """
    _run_git(["fetch", "--depth", "1", "origin", sha], cwd=repo_path)
    _run_git(["checkout", sha], cwd=repo_path)


# ---------------------------------------------------------------------------
# Commit & push report files back to the repo
# ---------------------------------------------------------------------------

# Files the pipeline generates that should be pushed back
_REPORT_FILES = [
    ".docrot-report.txt",
    ".docrot-report.json",
    ".docrot-fingerprints.json",
]


def commit_and_push_reports(
    repo_path: str,
    branch: str,
    commit_sha: str,
    token: Optional[str] = None,
    clone_url: Optional[str] = None,
) -> bool:
    """
    Stage the Docrot report files, commit them, and push back to the
    remote branch so users can see results in their repo.

    Only commits files that actually exist (e.g. on a clean first-run
    only the fingerprints file is created, no reports).

    Args:
        repo_path:  Absolute path to the local clone.
        branch:     Branch to push to.
        commit_sha: The commit that triggered this scan (for the message).
        token:      GitHub PAT — needed to push to the remote.
        clone_url:  Original HTTPS clone URL (used to set authenticated remote).

    Returns:
        True if the push succeeded, False otherwise.
    """
    # Figure out which report files actually exist
    files_to_add: List[str] = []
    for filename in _REPORT_FILES:
        if os.path.isfile(os.path.join(repo_path, filename)):
            files_to_add.append(filename)

    if not files_to_add:
        print("[git] No report files to push.")
        return False

    try:
        # Configure git identity for the commit (required in fresh clones)
        _run_git(["config", "user.email", "docrot-bot@users.noreply.github.com"], cwd=repo_path)
        _run_git(["config", "user.name", "Docrot Detector"], cwd=repo_path)

        # If we have a token, update the remote URL so push is authenticated
        if token and clone_url:
            auth_url = _authenticated_clone_url(clone_url, token)
            _run_git(["remote", "set-url", "origin", auth_url], cwd=repo_path)

        # Stage only the report files
        _run_git(["add"] + files_to_add, cwd=repo_path)

        # Check if there's actually anything to commit (avoids empty commits)
        result = _run_git(["diff", "--cached", "--quiet"], cwd=repo_path)
        # If diff --quiet exits 0, there are no staged changes
        print("[git] Report files unchanged — nothing to push.")
        return False

    except subprocess.CalledProcessError as e:
        # diff --quiet exits 1 when there ARE staged changes — that's the success path
        if e.cmd and "diff" in e.cmd and e.returncode == 1:
            pass  # There are changes to commit — continue below
        else:
            print(f"[git] Error during staging: {e.stderr}")
            return False

    try:
        # Commit
        short_sha = commit_sha[:8] if commit_sha else "unknown"
        commit_msg = f"[docrot] Update reports for {short_sha}\n\nAutomatically generated by Docrot Detector."
        _run_git(["commit", "-m", commit_msg], cwd=repo_path)

        # Push
        _run_git(["push", "origin", branch], cwd=repo_path)

        print(f"[git] Reports pushed to {branch}: {', '.join(files_to_add)}")
        return True

    except subprocess.CalledProcessError as e:
        print(f"[git] Failed to push reports: {e.stderr}")
        return False


# ---------------------------------------------------------------------------
# GitHub API — Find open PR for a branch
# ---------------------------------------------------------------------------

def find_open_pr_for_branch(
    repo_full_name: str,
    branch: str,
    token: str,
) -> Optional[int]:
    """
    Find an open pull request whose head branch matches `branch`.

    Args:
        repo_full_name: "owner/repo".
        branch:         Branch name (e.g. "feature-x").
        token:          GitHub personal access token.

    Returns:
        The PR number if one is found, or None.
    """
    url = f"{GITHUB_API_BASE}/repos/{repo_full_name}/pulls"
    params = {
        "state": "open",
        "head": f"{repo_full_name.split('/')[0]}:{branch}",
        "per_page": 1,
    }

    try:
        resp = requests.get(url, params=params, headers=_gh_headers(token), timeout=15)
        if resp.status_code == 200:
            prs = resp.json()
            if prs:
                pr_number = prs[0]["number"]
                print(f"[github] Found open PR #{pr_number} for branch '{branch}'")
                return pr_number
            else:
                print(f"[github] No open PR found for branch '{branch}'")
                return None
        else:
            print(f"[github] Failed to search PRs: {resp.status_code} {resp.text[:200]}")
            return None
    except requests.RequestException as exc:
        print(f"[github] Error searching PRs: {exc}")
        return None


# ---------------------------------------------------------------------------
# GitHub API — Commit Status
# ---------------------------------------------------------------------------


def post_commit_status(
    repo_full_name: str,
    sha: str,
    state: str,
    description: str,
    token: str,
    target_url: Optional[str] = None,
    context: str = "docrot-detector",
) -> bool:
    """
    Post a commit status to GitHub.

    This lets Docrot show pass/fail checks directly on commits and PRs.

    Args:
        repo_full_name: "owner/repo".
        sha:            Commit SHA to annotate.
        state:          One of "pending", "success", "failure", "error".
        description:    Short description (max 140 chars).
        token:          GitHub personal access token with repo:status scope.
        target_url:     Optional URL linking to a detailed report.
        context:        Status context string (default "docrot-detector").

    Returns:
        True if the status was posted successfully, False otherwise.
    """
    url = f"{GITHUB_API_BASE}/repos/{repo_full_name}/statuses/{sha}"

    payload = {
        "state": state,
        "description": description[:140],
        "context": context,
    }
    if target_url:
        payload["target_url"] = target_url

    try:
        resp = requests.post(url, json=payload, headers=_gh_headers(token), timeout=15)
        if resp.status_code == 201:
            print(f"[github] Commit status '{state}' posted for {sha[:8]}")
            return True
        else:
            print(
                f"[github] Failed to post commit status: "
                f"{resp.status_code} {resp.text[:200]}"
            )
            return False
    except requests.RequestException as exc:
        print(f"[github] Error posting commit status: {exc}")
        return False


def post_pr_comment(
    repo_full_name: str,
    pr_number: int,
    body: str,
    token: str,
) -> bool:
    """
    Post a comment on a GitHub pull request with scan results.

    Args:
        repo_full_name: "owner/repo".
        pr_number:      PR number (integer).
        body:           Markdown body of the comment.
        token:          GitHub personal access token.

    Returns:
        True if the comment was posted, False otherwise.
    """
    url = f"{GITHUB_API_BASE}/repos/{repo_full_name}/issues/{pr_number}/comments"

    try:
        resp = requests.post(url, json={"body": body}, headers=_gh_headers(token), timeout=15)
        if resp.status_code == 201:
            print(f"[github] Comment posted on PR #{pr_number}")
            return True
        else:
            print(
                f"[github] Failed to post PR comment: "
                f"{resp.status_code} {resp.text[:200]}"
            )
            return False
    except requests.RequestException as exc:
        print(f"[github] Error posting PR comment: {exc}")
        return False


# ---------------------------------------------------------------------------
# PR comment body formatter
# ---------------------------------------------------------------------------

def format_pr_comment(report_path: str, commit_sha: str) -> Optional[str]:
    """
    Read the .docrot-report.json and build a formatted Markdown comment
    suitable for posting on a GitHub PR.

    Args:
        report_path: Absolute path to .docrot-report.json.
        commit_sha:  The commit that triggered this scan.

    Returns:
        Markdown string, or None if the report doesn't exist or has no flags.
    """
    import json

    if not os.path.isfile(report_path):
        return None

    try:
        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    flags = report.get("issues", [])
    if not flags:
        return None

    # Count severities
    high = sum(1 for f in flags if f.get("severity") == "high")
    medium = sum(1 for f in flags if f.get("severity") == "medium")
    low = sum(1 for f in flags if f.get("severity") == "low")
    total = len(flags)

    # Build header
    short_sha = commit_sha[:8] if commit_sha else "unknown"
    if high > 0:
        header = f"## \u26a0\ufe0f Docrot Detector — {total} alert(s) found"
    else:
        header = f"## \U0001f4cb Docrot Detector — {total} alert(s) found"

    lines = [
        header,
        "",
        f"Scan triggered by commit `{short_sha}`",
        "",
        f"| Severity | Count |",
        f"|----------|-------|",
        f"| \U0001f534 High | {high} |",
        f"| \U0001f7e1 Medium | {medium} |",
        f"| \U0001f7e2 Low | {low} |",
        "",
    ]

    # List high-severity flags first, then medium, then low
    if high > 0:
        lines.append("### \U0001f534 High Severity")
        lines.append("")
        for f in flags:
            if f.get("severity") == "high":
                lines.append(f"- **{f.get('message', 'Unknown')}**")
                suggestion = f.get("suggestion", "")
                if suggestion:
                    lines.append(f"  - _Suggestion: {suggestion}_")
        lines.append("")

    if medium > 0:
        lines.append("### \U0001f7e1 Medium Severity")
        lines.append("")
        for f in flags:
            if f.get("severity") == "medium":
                lines.append(f"- {f.get('message', 'Unknown')}")
                suggestion = f.get("suggestion", "")
                if suggestion:
                    lines.append(f"  - _Suggestion: {suggestion}_")
        lines.append("")

    if low > 0:
        lines.append("### \U0001f7e2 Low Severity")
        lines.append("")
        for f in flags:
            if f.get("severity") == "low":
                lines.append(f"- {f.get('message', 'Unknown')}")
        lines.append("")

    # AI suggestions section
    ai_suggestions = report.get("ai_suggestions", [])
    if ai_suggestions:
        lines.append("### 🤖 AI-Generated Suggestions")
        lines.append("")
        lines.append("> **Note:** These suggestions are AI-generated — review before applying.")
        lines.append("")
        for s in ai_suggestions:
            doc_path = s.get("doc_path", "unknown")
            triggered_by = s.get("triggered_by", [])
            suggestion_text = s.get("suggestion", "")
            model_used = s.get("model_used", "")

            lines.append(f"<details>")
            lines.append(f"<summary><strong>{doc_path}</strong></summary>")
            lines.append("")
            if triggered_by:
                lines.append(f"Triggered by: `{'`, `'.join(triggered_by)}`")
                lines.append("")
            lines.append(suggestion_text)
            lines.append("")
            lines.append("</details>")
            lines.append("")

        if ai_suggestions:
            lines.append(f"_Model: {ai_suggestions[0].get('model_used', 'unknown')}_")
            lines.append("")

    lines.append("---")
    lines.append("_Automatically generated by [Docrot Detector](https://github.com/SuchiiJain/CS4485_Capstone). "
                 "See `.docrot-report.json` for full details._")

    return "\n".join(lines)
