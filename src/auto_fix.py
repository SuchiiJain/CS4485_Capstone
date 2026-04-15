"""
Auto-Fix Orchestrator — close the loop from detection to remediation.

This module turns a stored Docrot flag into an actual pull request
against the user's repository. It ties together three existing pieces:

    1. `patch_generator` — produces a deterministic doc patch from the
       structural data captured by the scanner.
    2. `pr_creator`      — wraps the GitHub REST API to create a branch,
       commit the patched file, and open a pull request.
    3. Firestore flag data — the already-persisted record of what the
       scanner detected on a given commit.

The orchestrator is intentionally usable three ways:

    * Programmatically (from the Cloud Function or a test)
    * As a CLI: `python -m src.auto_fix --repo owner/r --flag-json f.json`
    * Dry-run: prints the patched doc to stdout without touching GitHub

Auth model:
    The caller supplies a GitHub access token. This is typically a user's
    OAuth token with `repo` scope requested at login. We never call
    GitHub anonymously.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

from .patch_generator import DocPatch, generate_patch, describe_unsupported
from .pr_creator import (
    GitHubAPIError,
    GitHubPRCreator,
    build_branch_name,
)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class AutoFixResult:
    """Outcome of a single apply-fix attempt."""

    success: bool
    reason: str
    pr_url: Optional[str] = None
    pr_number: Optional[int] = None
    branch: Optional[str] = None
    doc_path: Optional[str] = None
    summary: Optional[str] = None
    todo_notes: Optional[list] = None
    error: Optional[str] = None

    def to_json(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


# ---------------------------------------------------------------------------
# Messages used in commit + PR metadata
# ---------------------------------------------------------------------------


PR_TITLE_TEMPLATE = "Docrot: update docs for `{symbol}` ({reason})"
COMMIT_MESSAGE_TEMPLATE = "docrot: update `{doc_path}` for `{symbol}`"


def _build_pr_body(
    patch: DocPatch,
    flag: Dict[str, Any],
    commit_hash: Optional[str],
) -> str:
    """Construct the PR body with flag context and TODO notes."""
    lines = [
        "This pull request was generated automatically by "
        "**Docrot Detector**.",
        "",
        "### Change detected",
        f"- **Reason:** `{patch.reason}`",
        f"- **Symbol:** `{patch.symbol}`",
        f"- **Source file:** `{flag.get('file_path', '(unknown)')}`",
        f"- **Doc file:** `{patch.doc_path}`",
    ]

    if commit_hash:
        lines.append(f"- **Detected on commit:** `{commit_hash[:8]}`")

    lines.extend(["", "### What changed", f"- {patch.summary}", ""])

    if patch.todo_notes:
        lines.append("### Reviewer notes")
        for note in patch.todo_notes:
            lines.append(f"- {note}")
        lines.append("")

    lines.extend(
        [
            "### How to review",
            "- The scanner produced this patch using deterministic rules on",
            "  the old/new structural data of the flagged symbol.",
            "- No AI was used to produce the diff itself; AI suggestions",
            "  appear separately in the Docrot dashboard.",
            "- Feel free to edit this branch before merging.",
        ]
    )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def apply_fix(
    flag: Dict[str, Any],
    repo_full_name: str,
    token: str,
    *,
    base_branch: Optional[str] = None,
    commit_hash: Optional[str] = None,
    flag_id: Optional[str] = None,
    dry_run: bool = False,
    creator: Optional[GitHubPRCreator] = None,
) -> AutoFixResult:
    """
    Apply a single flag's fix end-to-end and return the outcome.

    Args:
        flag: Flag data dict (same shape as stored in Firestore).
        repo_full_name: GitHub "owner/repo" string to open the PR on.
        token: GitHub access token with contents + pull_requests write.
        base_branch: Base branch for the PR (default: repo default branch).
        commit_hash: The commit that originally produced the flag.
        flag_id: Stable flag identifier (used to name the branch).
        dry_run: If True, generate the patch but do not call GitHub.
        creator: Injected client for testing.

    Returns:
        AutoFixResult describing what happened.
    """
    doc_path = flag.get("doc_file")
    symbol = flag.get("symbol", "")

    if not doc_path:
        return AutoFixResult(
            success=False,
            reason=flag.get("reason", "unknown"),
            error="Flag has no `doc_file`; cannot locate target documentation.",
        )

    if dry_run and creator is None:
        return _dry_run_without_network(flag, repo_full_name, token, commit_hash)

    client = creator or GitHubPRCreator(token, repo_full_name)

    try:
        resolved_base = base_branch or client.get_default_branch()
        current_file = client.get_file(doc_path, resolved_base)
    except GitHubAPIError as exc:
        return AutoFixResult(
            success=False,
            reason=flag.get("reason", "unknown"),
            doc_path=doc_path,
            error=f"Failed to fetch {doc_path}: {exc}",
        )

    patch = generate_patch(flag, current_file.content)
    if patch is None:
        return AutoFixResult(
            success=False,
            reason=flag.get("reason", "unknown"),
            doc_path=doc_path,
            error=describe_unsupported(flag),
        )

    if patch.is_noop:
        return AutoFixResult(
            success=False,
            reason=patch.reason,
            doc_path=doc_path,
            summary=patch.summary,
            error="Patch produced no changes against the current doc content.",
        )

    if dry_run:
        return AutoFixResult(
            success=True,
            reason=patch.reason,
            doc_path=doc_path,
            summary=patch.summary,
            todo_notes=patch.todo_notes,
            branch=None,
            pr_url=None,
        )

    branch_name = build_branch_name(flag_id or symbol, symbol)
    title = PR_TITLE_TEMPLATE.format(symbol=symbol, reason=patch.reason)
    body = _build_pr_body(patch, flag, commit_hash)
    commit_message = COMMIT_MESSAGE_TEMPLATE.format(
        doc_path=doc_path, symbol=symbol
    )

    try:
        client.ensure_branch(resolved_base, branch_name)
        client.update_file(
            path=doc_path,
            content=patch.patched_content,
            branch=branch_name,
            message=commit_message,
            expected_sha=current_file.sha,
        )
    except GitHubAPIError as exc:
        return AutoFixResult(
            success=False,
            reason=patch.reason,
            doc_path=doc_path,
            branch=branch_name,
            summary=patch.summary,
            error=f"Commit failed: {exc}",
        )

    existing = client.find_open_pr(branch_name)
    if existing:
        return AutoFixResult(
            success=True,
            reason=patch.reason,
            doc_path=doc_path,
            branch=branch_name,
            summary=patch.summary,
            todo_notes=patch.todo_notes,
            pr_url=existing.get("html_url"),
            pr_number=existing.get("number"),
        )

    try:
        pr = client.create_pull_request(
            base=resolved_base,
            head=branch_name,
            title=title,
            body=body,
        )
    except GitHubAPIError as exc:
        return AutoFixResult(
            success=False,
            reason=patch.reason,
            doc_path=doc_path,
            branch=branch_name,
            summary=patch.summary,
            error=f"PR creation failed: {exc}",
        )

    return AutoFixResult(
        success=True,
        reason=patch.reason,
        doc_path=doc_path,
        branch=branch_name,
        summary=patch.summary,
        todo_notes=patch.todo_notes,
        pr_url=pr.get("html_url"),
        pr_number=pr.get("number"),
    )


def _dry_run_without_network(
    flag: Dict[str, Any],
    repo_full_name: str,
    token: str,
    commit_hash: Optional[str],
) -> AutoFixResult:
    """
    Dry-run path used when --dry-run is requested AND no creator was
    injected. We still need the current file to generate a patch, but
    we avoid side effects (no branch, no commit, no PR).
    """
    doc_path = flag.get("doc_file", "")
    try:
        client = GitHubPRCreator(token, repo_full_name)
        base = client.get_default_branch()
        current = client.get_file(doc_path, base)
    except GitHubAPIError as exc:
        return AutoFixResult(
            success=False,
            reason=flag.get("reason", "unknown"),
            doc_path=doc_path,
            error=f"Dry-run fetch failed: {exc}",
        )

    patch = generate_patch(flag, current.content)
    if patch is None:
        return AutoFixResult(
            success=False,
            reason=flag.get("reason", "unknown"),
            doc_path=doc_path,
            error=describe_unsupported(flag),
        )

    return AutoFixResult(
        success=not patch.is_noop,
        reason=patch.reason,
        doc_path=doc_path,
        summary=patch.summary,
        todo_notes=patch.todo_notes,
        branch=None,
        pr_url=None,
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _load_flag(flag_json_path: str) -> Dict[str, Any]:
    with open(flag_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        return data
    raise ValueError("Flag JSON must be a single object.")


def _main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m src.auto_fix",
        description=(
            "Apply a deterministic Docrot doc patch to a target repo by "
            "opening a pull request. Requires a GitHub token (env "
            "GITHUB_TOKEN) with contents + pull_requests write scope."
        ),
    )
    parser.add_argument("--repo", required=True, help="owner/repo")
    parser.add_argument(
        "--flag-json",
        required=True,
        help="Path to a JSON file describing the flag (same shape as Firestore).",
    )
    parser.add_argument(
        "--base-branch",
        help="Branch to base the PR on (defaults to the repo default).",
    )
    parser.add_argument("--commit-hash", help="Optional commit hash for context.")
    parser.add_argument("--flag-id", help="Optional flag id for branch naming.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate and summarise the patch without creating a branch or PR.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the result as JSON on stdout (for scripting).",
    )

    args = parser.parse_args(argv)

    token = os.environ.get("GITHUB_TOKEN", "")
    if not token and not args.dry_run:
        print("[auto-fix] GITHUB_TOKEN env var is required.", file=sys.stderr)
        return 2

    flag = _load_flag(args.flag_json)
    result = apply_fix(
        flag,
        repo_full_name=args.repo,
        token=token,
        base_branch=args.base_branch,
        commit_hash=args.commit_hash,
        flag_id=args.flag_id,
        dry_run=args.dry_run,
    )

    if args.json:
        print(json.dumps(result.to_json(), indent=2))
    else:
        _print_human_result(result)

    return 0 if result.success else 1


def _print_human_result(result: AutoFixResult) -> None:
    tag = "[auto-fix]"
    if not result.success:
        print(f"{tag} FAILED — {result.error}", file=sys.stderr)
        return
    print(f"{tag} Patch applied for reason `{result.reason}`")
    if result.doc_path:
        print(f"{tag} Doc: {result.doc_path}")
    if result.summary:
        print(f"{tag} Summary: {result.summary}")
    if result.branch:
        print(f"{tag} Branch: {result.branch}")
    if result.pr_url:
        print(f"{tag} PR: {result.pr_url}")
    if result.todo_notes:
        print(f"{tag} Reviewer notes:")
        for note in result.todo_notes:
            print(f"  - {note}")


if __name__ == "__main__":
    raise SystemExit(_main())
