"""
Webhook Server — Flask app that receives GitHub push events and triggers
the Docrot Detector pipeline.

Setup (GitHub side):
    1. Go to your repo → Settings → Webhooks → Add webhook
    2. Payload URL: http://<your-server>:5000/webhook
    3. Content type: application/json
    4. Secret: <same value as DOCROT_WEBHOOK_SECRET env var>
    5. Events: select "Just the push event"

Environment variables:
    DOCROT_WEBHOOK_SECRET   — shared secret for HMAC-SHA256 signature verification
    DOCROT_CLONE_DIR        — directory to clone repos into (default: ./repos)
    GITHUB_TOKEN            — (optional) GitHub personal access token for
                              posting commit statuses back to the repo

Usage:
    python -m src.webhook_server            # start on default port 5000
    DOCROT_PORT=8080 python -m src.webhook_server   # custom port
"""

import hashlib
import hmac
import json
import os
import sys
import threading
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from flask import Flask, Request, Response, jsonify, request

from src.github_integration import (
    clone_or_pull_repo,
    commit_and_push_reports,
    find_open_pr_for_branch,
    format_pr_comment,
    post_commit_status,
    post_pr_comment,
)
from src.run import run as run_pipeline


# ---------------------------------------------------------------------------
# Load .env file (if it exists) so you don't have to set env vars manually
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv
    load_dotenv()  # reads .env from the current working directory
except ImportError:
    pass  # python-dotenv not installed — fall back to manual env vars


# ---------------------------------------------------------------------------
# App configuration
# ---------------------------------------------------------------------------

app = Flask(__name__)

WEBHOOK_SECRET: Optional[str] = os.environ.get("DOCROT_WEBHOOK_SECRET")
CLONE_DIR: str = os.environ.get("DOCROT_CLONE_DIR", os.path.join(os.getcwd(), "repos"))
GITHUB_TOKEN: Optional[str] = os.environ.get("GITHUB_TOKEN")

# Per-repo locks to prevent overlapping pipeline runs on the same clone
_repo_locks: Dict[str, threading.Lock] = {}
_repo_locks_guard = threading.Lock()


# ---------------------------------------------------------------------------
# Signature verification
# ---------------------------------------------------------------------------

def _verify_signature(payload_body: bytes, signature_header: Optional[str]) -> bool:
    """
    Verify the GitHub webhook HMAC-SHA256 signature.

    Args:
        payload_body:     Raw request body bytes.
        signature_header: Value of the X-Hub-Signature-256 header.

    Returns:
        True if the signature is valid, False otherwise.
    """
    if not WEBHOOK_SECRET:
        print("[webhook] Warning: DOCROT_WEBHOOK_SECRET not set — skipping signature verification.")
        return True

    if not signature_header:
        return False

    expected = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode("utf-8"),
        payload_body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature_header)


# ---------------------------------------------------------------------------
# Payload parsing helpers
# ---------------------------------------------------------------------------

def _parse_push_event(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract the fields we care about from a GitHub push event payload.

    Returns:
        Dict with keys:
            repo_full_name  — "owner/repo"
            clone_url       — HTTPS clone URL
            branch          — short branch name (e.g. "main")
            head_commit_sha — SHA of the latest commit in the push
            head_commit_msg — commit message
            pusher          — username of the pusher
    """
    repo = payload.get("repository", {})
    ref = payload.get("ref", "")                 # e.g. "refs/heads/main"
    branch = ref.replace("refs/heads/", "")

    head_commit = payload.get("head_commit") or {}

    # Get committer name from the head commit (used to detect Docrot's own pushes)
    committer_name = head_commit.get("committer", {}).get("name", "")

    return {
        "repo_full_name": repo.get("full_name", "unknown/unknown"),
        "clone_url": repo.get("clone_url", ""),
        "branch": branch,
        "head_commit_sha": head_commit.get("id", payload.get("after", "")),
        "head_commit_msg": head_commit.get("message", ""),
        "head_commit_committer": committer_name,
        "pusher": payload.get("pusher", {}).get("name", "unknown"),
    }


# ---------------------------------------------------------------------------
# Background pipeline runner
# ---------------------------------------------------------------------------

def _run_pipeline_async(push_info: Dict[str, Any]) -> None:
    """
    Clone/pull the repo, run the Docrot pipeline, and optionally post a
    commit status back to GitHub.  Runs in a background thread so the
    webhook can return 202 immediately.
    """
    repo_name = push_info["repo_full_name"]
    sha = push_info["head_commit_sha"]
    branch = push_info["branch"]

    # Acquire a per-repo lock so two pushes to the same repo don't
    # stomp on each other's git operations.
    with _repo_locks_guard:
        if repo_name not in _repo_locks:
            _repo_locks[repo_name] = threading.Lock()
        lock = _repo_locks[repo_name]

    if not lock.acquire(blocking=False):
        print(f"[webhook] Skipping {repo_name}@{sha[:8]} — another scan is already running.")
        sys.stdout.flush()
        return

    try:
        _run_pipeline_locked(push_info, repo_name, sha, branch)
    finally:
        lock.release()


def _run_pipeline_locked(
    push_info: Dict[str, Any],
    repo_name: str,
    sha: str,
    branch: str,
) -> None:
    """Inner pipeline logic, called while holding the per-repo lock."""
    print(f"[webhook] Starting pipeline for {repo_name}@{branch} ({sha[:8]})")
    sys.stdout.flush()

    # 1. Post "pending" commit status
    if GITHUB_TOKEN:
        post_commit_status(
            repo_full_name=repo_name,
            sha=sha,
            state="pending",
            description="Docrot Detector scan in progress…",
            token=GITHUB_TOKEN,
        )

    try:
        # 2. Clone or pull the repo
        repo_path = clone_or_pull_repo(
            clone_url=push_info["clone_url"],
            repo_full_name=repo_name,
            branch=branch,
            clone_dir=CLONE_DIR,
            token=GITHUB_TOKEN,
        )

        # 3. Run the existing pipeline
        exit_code = run_pipeline(repo_path, commit_hash=sha)

        # 4. Push report files back to the repo
        pushed = commit_and_push_reports(
            repo_path=repo_path,
            branch=branch,
            commit_sha=sha,
            token=GITHUB_TOKEN,
            clone_url=push_info["clone_url"],
        )
        if pushed:
            print(f"[webhook] Reports pushed to {repo_name}@{branch}")
        sys.stdout.flush()

        # 5. Comment on PR (if one exists for this branch)
        if GITHUB_TOKEN and exit_code == 1:
            import os as _os
            report_json_path = _os.path.join(repo_path, ".docrot-report.json")
            pr_number = find_open_pr_for_branch(repo_name, branch, GITHUB_TOKEN)
            if pr_number:
                comment_body = format_pr_comment(report_json_path, sha)
                if comment_body:
                    post_pr_comment(repo_name, pr_number, comment_body, GITHUB_TOKEN)
        sys.stdout.flush()

        # 6. Post result back as commit status
        if GITHUB_TOKEN:
            if exit_code == 0:
                state, desc = "success", "No documentation rot detected."
            elif exit_code == 1:
                state, desc = "failure", "Documentation may be stale — review report."
            else:
                state, desc = "error", "Docrot scan encountered an error."

            post_commit_status(
                repo_full_name=repo_name,
                sha=sha,
                state=state,
                description=desc,
                token=GITHUB_TOKEN,
            )

        print(f"[webhook] Pipeline finished for {repo_name}@{sha[:8]} — exit code {exit_code}")
        sys.stdout.flush()

    except Exception as exc:
        print(f"[webhook] Pipeline error for {repo_name}@{sha[:8]}: {exc}")
        traceback.print_exc()
        sys.stdout.flush()

        if GITHUB_TOKEN:
            post_commit_status(
                repo_full_name=repo_name,
                sha=sha,
                state="error",
                description=f"Docrot scan failed: {exc}",
                token=GITHUB_TOKEN,
            )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/webhook", methods=["POST"])
def webhook():
    """
    Receive a GitHub webhook event.

    Only `push` events are processed; all others are acknowledged and ignored.
    The actual pipeline work runs in a background thread so GitHub gets a
    fast 202 response.
    """
    # 1. Verify signature
    sig = request.headers.get("X-Hub-Signature-256")
    if not _verify_signature(request.get_data(), sig):
        return jsonify({"error": "Invalid signature"}), 403

    # 2. Determine event type
    event_type = request.headers.get("X-GitHub-Event", "")
    if event_type == "ping":
        return jsonify({"status": "pong"}), 200

    if event_type != "push":
        return jsonify({"status": f"ignored event: {event_type}"}), 200

    # 3. Parse payload
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"error": "Invalid or missing JSON payload"}), 400

    push_info = _parse_push_event(payload)

    # Ignore branch deletions (after == "0000...")
    if push_info["head_commit_sha"].startswith("0000000"):
        return jsonify({"status": "branch deletion ignored"}), 200

    # Ignore commits pushed by Docrot itself (prevent infinite loop)
    is_docrot_commit = (
        push_info["head_commit_msg"].startswith("[docrot]")
        or push_info["head_commit_committer"] == "Docrot Detector"
        or push_info["pusher"] == "Docrot Detector"
    )
    if is_docrot_commit:
        print(f"[webhook] Ignoring Docrot's own push ({push_info['head_commit_sha'][:8]})")
        sys.stdout.flush()
        return jsonify({"status": "ignoring docrot's own commit"}), 200

    print(
        f"[webhook] Received push: {push_info['repo_full_name']} "
        f"branch={push_info['branch']} "
        f"sha={push_info['head_commit_sha'][:8]} "
        f"by {push_info['pusher']}"
    )

    # 4. Kick off pipeline in background thread
    thread = threading.Thread(
        target=_run_pipeline_async,
        args=(push_info,),
        daemon=True,
    )
    thread.start()

    return jsonify({
        "status": "accepted",
        "repo": push_info["repo_full_name"],
        "branch": push_info["branch"],
        "sha": push_info["head_commit_sha"],
    }), 202


@app.route("/health", methods=["GET"])
def health():
    """Simple health-check endpoint."""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }), 200


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    port = int(os.environ.get("DOCROT_PORT", 5000))
    debug = os.environ.get("DOCROT_DEBUG", "false").lower() == "true"

    # Ensure clone directory exists
    os.makedirs(CLONE_DIR, exist_ok=True)

    print(f"[webhook] Docrot Webhook Server starting on port {port}")
    print(f"[webhook] Clone directory: {CLONE_DIR}")
    print(f"[webhook] Signature verification: {'enabled' if WEBHOOK_SECRET else 'DISABLED (set DOCROT_WEBHOOK_SECRET)'}")
    print(f"[webhook] Commit status posting: {'enabled' if GITHUB_TOKEN else 'disabled (set GITHUB_TOKEN)'}")

    app.run(host="0.0.0.0", port=port, debug=debug)


if __name__ == "__main__":
    main()
