"""
GitHub Integration — Git operations and GitHub API helpers for the
Docrot Detector webhook pipeline.

Responsibilities:
    - Clone a repository (or pull latest if already cloned)
    - Checkout the correct branch / commit
    - Post commit statuses to GitHub via the REST API

Dependencies:
    - git CLI must be available on PATH
    - `requests` library for GitHub API calls
"""

import os
import shutil
import subprocess
from typing import Optional

import requests


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
            "--depth", "1",
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
# GitHub API — Commit Status
# ---------------------------------------------------------------------------

GITHUB_API_BASE = "https://api.github.com"


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

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
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

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    try:
        resp = requests.post(url, json={"body": body}, headers=headers, timeout=15)
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
