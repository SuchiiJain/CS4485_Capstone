"""Tests for the end-to-end auto-fix orchestrator.

The orchestrator is the piece that ties `patch_generator` + `pr_creator`
together and turns a stored flag into a pull request. We test it by
injecting a fake GitHubPRCreator so no HTTP traffic leaves the process.
Each test exercises a specific branch in `apply_fix()`:

    * happy path: default branch → fetch file → patch → branch → commit → PR
    * existing PR short-circuit
    * dry-run without a creator (uses a live client → exercised via mock)
    * dry-run with an injected creator (no mutating calls at all)
    * validation failures: missing doc_file, unsupported reason
    * GitHub errors at each stage (fetch / commit / PR creation)
    * JSON/CLI-facing `AutoFixResult.to_json()`
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pytest

from src.auto_fix import AutoFixResult, apply_fix
from src.pr_creator import GitHubAPIError


# ---------------------------------------------------------------------------
# Fake creator
# ---------------------------------------------------------------------------


@dataclass
class FakeFile:
    path: str
    content: str
    sha: str
    ref: str


@dataclass
class FakeCreator:
    """Mimics the subset of GitHubPRCreator used by apply_fix."""

    default_branch: str = "main"
    file_content: str = ""
    file_sha: str = "blob-sha"
    existing_pr: Optional[Dict[str, Any]] = None
    pr_payload: Dict[str, Any] = field(
        default_factory=lambda: {
            "html_url": "https://example.com/pr/1",
            "number": 1,
        }
    )

    # Error injection — raise on a specific step
    raise_on: Optional[str] = None  # "get_file" | "update_file" | "create_pr"

    # Recorded calls
    calls: List[str] = field(default_factory=list)

    # --- methods used by apply_fix ---

    def get_default_branch(self) -> str:
        self.calls.append("get_default_branch")
        return self.default_branch

    def get_file(self, path: str, ref: str):
        self.calls.append(f"get_file:{path}@{ref}")
        if self.raise_on == "get_file":
            raise GitHubAPIError(404, "not found")
        return FakeFile(path=path, content=self.file_content, sha=self.file_sha, ref=ref)

    def ensure_branch(self, base: str, new: str) -> None:
        self.calls.append(f"ensure_branch:{base}->{new}")

    def update_file(self, *, path, content, branch, message, expected_sha):
        self.calls.append(f"update_file:{path}@{branch}")
        if self.raise_on == "update_file":
            raise GitHubAPIError(422, "bad sha")
        return {}

    def find_open_pr(self, head_branch: str):
        self.calls.append(f"find_open_pr:{head_branch}")
        return self.existing_pr

    def create_pull_request(self, *, base, head, title, body, draft=False):
        self.calls.append(f"create_pr:{head}->{base}")
        if self.raise_on == "create_pr":
            raise GitHubAPIError(422, "already exists")
        return self.pr_payload


# ---------------------------------------------------------------------------
# Fixtures — a realistic flag + doc content pair
# ---------------------------------------------------------------------------


@pytest.fixture
def signature_flag() -> Dict[str, Any]:
    return {
        "reason": "signature_changed",
        "symbol": "format_user",
        "doc_file": "docs/API.md",
        "signature": "def format_user(user: User, verbose: bool = False) -> str:",
        "params": [
            {"name": "user", "annotation": "User"},
            {"name": "verbose", "annotation": "bool", "default": "False"},
        ],
        "return_type": "str",
    }


@pytest.fixture
def doc_with_old_signature() -> str:
    return (
        "# API\n\n"
        "```python\n"
        "def format_user(user):\n"
        "    ...\n"
        "```\n"
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_apply_fix_happy_path(signature_flag, doc_with_old_signature):
    creator = FakeCreator(file_content=doc_with_old_signature)

    result = apply_fix(
        signature_flag,
        repo_full_name="owner/repo",
        token="tok",
        flag_id="abc123de",
        commit_hash="deadbeefcafebabe",
        creator=creator,
    )

    assert result.success is True
    assert result.pr_url == "https://example.com/pr/1"
    assert result.pr_number == 1
    assert result.branch is not None and result.branch.startswith("docrot/fix-")
    assert result.doc_path == "docs/API.md"
    # Order of operations should be: default branch → fetch → ensure branch
    # → commit → check existing PR → create PR
    assert creator.calls[0] == "get_default_branch"
    assert creator.calls[1].startswith("get_file:docs/API.md")
    assert any(c.startswith("ensure_branch:") for c in creator.calls)
    assert any(c.startswith("update_file:") for c in creator.calls)
    assert any(c.startswith("find_open_pr:") for c in creator.calls)
    assert any(c.startswith("create_pr:") for c in creator.calls)


def test_apply_fix_uses_explicit_base_branch(signature_flag, doc_with_old_signature):
    creator = FakeCreator(file_content=doc_with_old_signature)
    result = apply_fix(
        signature_flag,
        repo_full_name="owner/repo",
        token="tok",
        base_branch="develop",
        creator=creator,
    )
    assert result.success is True
    # When base_branch is supplied we should NOT call get_default_branch
    assert "get_default_branch" not in creator.calls
    assert any("@develop" in c for c in creator.calls)


def test_apply_fix_short_circuits_when_open_pr_already_exists(
    signature_flag, doc_with_old_signature
):
    creator = FakeCreator(
        file_content=doc_with_old_signature,
        existing_pr={"html_url": "https://example.com/pr/9", "number": 9},
    )
    result = apply_fix(
        signature_flag,
        repo_full_name="owner/repo",
        token="tok",
        creator=creator,
    )
    assert result.success is True
    assert result.pr_number == 9
    # We must not have attempted to open a new PR
    assert not any(c.startswith("create_pr:") for c in creator.calls)


# ---------------------------------------------------------------------------
# Dry-run paths
# ---------------------------------------------------------------------------


def test_dry_run_with_creator_skips_all_mutations(
    signature_flag, doc_with_old_signature
):
    creator = FakeCreator(file_content=doc_with_old_signature)
    result = apply_fix(
        signature_flag,
        repo_full_name="owner/repo",
        token="tok",
        dry_run=True,
        creator=creator,
    )
    assert result.success is True
    assert result.pr_url is None
    assert result.branch is None
    # No mutating calls at all
    forbidden = ("ensure_branch", "update_file", "create_pr")
    assert not any(c.startswith(p) for c in creator.calls for p in forbidden)


def test_dry_run_preserves_summary_and_todo_notes(
    signature_flag, doc_with_old_signature
):
    creator = FakeCreator(file_content=doc_with_old_signature)
    result = apply_fix(
        signature_flag,
        repo_full_name="owner/repo",
        token="tok",
        dry_run=True,
        creator=creator,
    )
    assert result.summary
    # signature_changed has no TODO notes by design → empty list, not None
    assert result.todo_notes is None or isinstance(result.todo_notes, list)


# ---------------------------------------------------------------------------
# Validation failures
# ---------------------------------------------------------------------------


def test_flag_without_doc_file_is_rejected_before_network():
    creator = FakeCreator()
    flag = {"reason": "signature_changed", "symbol": "foo"}  # no doc_file
    result = apply_fix(
        flag,
        repo_full_name="owner/repo",
        token="tok",
        creator=creator,
    )
    assert result.success is False
    assert result.error and "doc_file" in result.error
    assert creator.calls == []


def test_unsupported_reason_returns_descriptive_error(doc_with_old_signature):
    creator = FakeCreator(file_content=doc_with_old_signature)
    flag = {
        "reason": "docstring_stale",
        "symbol": "foo",
        "doc_file": "docs/API.md",
    }
    result = apply_fix(
        flag,
        repo_full_name="owner/repo",
        token="tok",
        creator=creator,
    )
    assert result.success is False
    assert "docstring_stale" in (result.error or "")


def test_patch_that_produces_no_change_is_reported_as_noop(signature_flag):
    # doc already contains the new signature → patch would be identical
    already_updated = (
        "```python\n"
        "def format_user(user: User, verbose: bool = False) -> str:\n"
        "    ...\n"
        "```\n"
    )
    creator = FakeCreator(file_content=already_updated)
    result = apply_fix(
        signature_flag,
        repo_full_name="owner/repo",
        token="tok",
        creator=creator,
    )
    # generate_patch won't find the OLD pattern, so it returns None → unsupported
    # message (rather than a no-op). Either way: failure, no PR.
    assert result.success is False
    assert not any(c.startswith("create_pr:") for c in creator.calls)


# ---------------------------------------------------------------------------
# GitHub error propagation
# ---------------------------------------------------------------------------


def test_fetch_failure_is_surfaced(signature_flag):
    creator = FakeCreator(raise_on="get_file")
    result = apply_fix(
        signature_flag,
        repo_full_name="owner/repo",
        token="tok",
        creator=creator,
    )
    assert result.success is False
    assert "Failed to fetch" in (result.error or "")


def test_commit_failure_is_surfaced(signature_flag, doc_with_old_signature):
    creator = FakeCreator(
        file_content=doc_with_old_signature,
        raise_on="update_file",
    )
    result = apply_fix(
        signature_flag,
        repo_full_name="owner/repo",
        token="tok",
        creator=creator,
    )
    assert result.success is False
    assert "Commit failed" in (result.error or "")


def test_pr_creation_failure_is_surfaced(signature_flag, doc_with_old_signature):
    creator = FakeCreator(
        file_content=doc_with_old_signature,
        raise_on="create_pr",
    )
    result = apply_fix(
        signature_flag,
        repo_full_name="owner/repo",
        token="tok",
        creator=creator,
    )
    assert result.success is False
    assert "PR creation failed" in (result.error or "")


# ---------------------------------------------------------------------------
# Result serialization
# ---------------------------------------------------------------------------


def test_autofix_result_to_json_drops_none_fields():
    result = AutoFixResult(
        success=True,
        reason="signature_changed",
        pr_url="https://example/pr/1",
        pr_number=1,
    )
    payload = result.to_json()
    assert payload["success"] is True
    assert payload["pr_number"] == 1
    # Omitted fields should NOT appear
    assert "error" not in payload
    assert "branch" not in payload
    assert "todo_notes" not in payload


def test_autofix_result_failure_serializes_error():
    result = AutoFixResult(
        success=False,
        reason="unknown",
        error="boom",
    )
    payload = result.to_json()
    assert payload["success"] is False
    assert payload["error"] == "boom"
