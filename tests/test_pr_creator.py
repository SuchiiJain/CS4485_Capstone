"""Tests for the GitHub REST wrapper used by the auto-fix orchestrator.

These tests never hit the real network. Instead, they inject a fake
session that records every call and returns scripted responses. That
lets us assert both:

    * the exact URL / method / payload the wrapper sends, and
    * how it interprets the various possible GitHub responses
      (success, 404, 422, empty body).

Covered surface:
    sanitize_branch_name, build_branch_name
    get_default_branch, get_ref_sha, branch_exists, ensure_branch
    get_file (including base64 decoding)
    update_file (with and without expected_sha)
    create_pull_request, find_open_pr
    GitHubAPIError for non-2xx responses
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pytest

from src.pr_creator import (
    GitHubAPIError,
    GitHubPRCreator,
    build_branch_name,
    sanitize_branch_name,
)


# ---------------------------------------------------------------------------
# Fake requests.Session
# ---------------------------------------------------------------------------


@dataclass
class FakeResponse:
    status_code: int = 200
    body: Any = None

    @property
    def content(self) -> bytes:
        if self.body is None:
            return b""
        return json.dumps(self.body).encode("utf-8")

    @property
    def text(self) -> str:
        if self.body is None:
            return ""
        return json.dumps(self.body)

    def json(self):
        if self.body is None:
            raise ValueError("No JSON body")
        return self.body


@dataclass
class RecordedCall:
    method: str
    url: str
    headers: Dict[str, str]
    json_body: Optional[Dict[str, Any]]
    params: Optional[Dict[str, Any]]


@dataclass
class FakeSession:
    """Scriptable stand-in for requests.Session used by the wrapper."""

    responses: List[FakeResponse] = field(default_factory=list)
    calls: List[RecordedCall] = field(default_factory=list)

    def queue(self, *responses: FakeResponse) -> None:
        self.responses.extend(responses)

    def request(
        self,
        method: str,
        url: str,
        headers=None,
        json=None,
        params=None,
        timeout=None,
    ) -> FakeResponse:
        self.calls.append(
            RecordedCall(
                method=method,
                url=url,
                headers=dict(headers or {}),
                json_body=json,
                params=params,
            )
        )
        if not self.responses:
            raise AssertionError(
                f"FakeSession got an unexpected {method} {url}; "
                "no scripted response was queued."
            )
        return self.responses.pop(0)


@pytest.fixture
def session() -> FakeSession:
    return FakeSession()


@pytest.fixture
def client(session: FakeSession) -> GitHubPRCreator:
    return GitHubPRCreator("tok", "octocat/hello-world", session=session)


# ---------------------------------------------------------------------------
# sanitize_branch_name / build_branch_name
# ---------------------------------------------------------------------------


def test_sanitize_replaces_unsafe_chars_with_dashes():
    assert sanitize_branch_name("feature/foo bar!") == "feature/foo-bar"


def test_sanitize_strips_leading_trailing_specials():
    assert sanitize_branch_name("--weird/./") == "weird"


def test_sanitize_empty_input_gets_timestamp_fallback():
    result = sanitize_branch_name("@@@")
    assert result.startswith("docrot-fix-")


def test_build_branch_name_format():
    branch = build_branch_name("a1b2c3d4e5", "format_user")
    assert branch.startswith("docrot/fix-a1b2c3d4-")
    assert branch.endswith("format_user")


def test_build_branch_name_truncates_long_flag_id():
    branch = build_branch_name("a" * 30, "sym")
    # only first 8 chars of the flag id should show up in the branch
    assert "-aaaaaaaa-" in branch
    assert "-aaaaaaaaa-" not in branch


# ---------------------------------------------------------------------------
# Construction guards
# ---------------------------------------------------------------------------


def test_constructor_requires_token():
    with pytest.raises(ValueError):
        GitHubPRCreator("", "owner/repo")


def test_constructor_requires_owner_repo_shape():
    with pytest.raises(ValueError):
        GitHubPRCreator("tok", "no-slash")


def test_constructor_sends_auth_header_on_every_call(client, session):
    session.queue(FakeResponse(200, {"default_branch": "main"}))
    client.get_default_branch()
    assert session.calls[0].headers["Authorization"] == "Bearer tok"
    assert session.calls[0].headers["Accept"] == "application/vnd.github+json"


# ---------------------------------------------------------------------------
# get_default_branch / get_ref_sha / branch_exists / ensure_branch
# ---------------------------------------------------------------------------


def test_get_default_branch_reads_field(client, session):
    session.queue(FakeResponse(200, {"default_branch": "develop"}))
    assert client.get_default_branch() == "develop"
    assert session.calls[-1].url.endswith("/repos/octocat/hello-world")


def test_get_default_branch_falls_back_to_main(client, session):
    session.queue(FakeResponse(200, {}))
    assert client.get_default_branch() == "main"


def test_get_ref_sha_returns_sha(client, session):
    session.queue(FakeResponse(200, {"object": {"sha": "abc123"}}))
    assert client.get_ref_sha("main") == "abc123"
    assert session.calls[-1].url.endswith("/git/ref/heads/main")


def test_branch_exists_true_on_200(client, session):
    session.queue(FakeResponse(200, {"object": {"sha": "x"}}))
    assert client.branch_exists("feature") is True


def test_branch_exists_false_on_404(client, session):
    session.queue(FakeResponse(404, {"message": "Not Found"}))
    assert client.branch_exists("nope") is False


def test_ensure_branch_no_op_when_branch_already_exists(client, session):
    session.queue(FakeResponse(200, {"object": {"sha": "x"}}))  # branch_exists
    client.ensure_branch("main", "existing")
    # Only the existence check was made; no POST to create.
    assert len(session.calls) == 1
    assert session.calls[0].method == "GET"


def test_ensure_branch_creates_ref_when_missing(client, session):
    session.queue(
        FakeResponse(404, {"message": "Not Found"}),   # branch_exists
        FakeResponse(200, {"object": {"sha": "base-sha"}}),  # get_ref_sha
        FakeResponse(201, {"ref": "refs/heads/new"}),  # create
    )
    client.ensure_branch("main", "new")
    create_call = session.calls[-1]
    assert create_call.method == "POST"
    assert create_call.url.endswith("/git/refs")
    assert create_call.json_body == {"ref": "refs/heads/new", "sha": "base-sha"}


# ---------------------------------------------------------------------------
# get_file
# ---------------------------------------------------------------------------


def test_get_file_decodes_base64(client, session):
    encoded = base64.b64encode("hello docs".encode("utf-8")).decode("ascii")
    session.queue(
        FakeResponse(
            200,
            {
                "path": "docs/API.md",
                "content": encoded,
                "encoding": "base64",
                "sha": "blob-sha",
            },
        )
    )
    file = client.get_file("docs/API.md", "main")
    assert file.content == "hello docs"
    assert file.sha == "blob-sha"
    assert file.ref == "main"
    assert session.calls[-1].params == {"ref": "main"}


def test_get_file_handles_non_base64_encoding(client, session):
    session.queue(
        FakeResponse(
            200,
            {"path": "x.md", "content": "plain", "encoding": "utf-8", "sha": "s"},
        )
    )
    file = client.get_file("x.md", "main")
    assert file.content == "plain"


# ---------------------------------------------------------------------------
# update_file
# ---------------------------------------------------------------------------


def test_update_file_uses_provided_sha_and_encodes_content(client, session):
    session.queue(FakeResponse(200, {"commit": {"sha": "new-commit"}}))
    client.update_file(
        path="docs/API.md",
        content="new",
        branch="feature",
        message="msg",
        expected_sha="old-sha",
    )
    call = session.calls[-1]
    assert call.method == "PUT"
    assert call.url.endswith("/contents/docs/API.md")
    assert call.json_body["sha"] == "old-sha"
    assert call.json_body["branch"] == "feature"
    assert base64.b64decode(call.json_body["content"]).decode("utf-8") == "new"


def test_update_file_fetches_sha_when_not_provided(client, session):
    session.queue(
        FakeResponse(
            200,
            {
                "path": "docs/API.md",
                "content": base64.b64encode(b"old").decode("ascii"),
                "encoding": "base64",
                "sha": "fetched-sha",
            },
        ),
        FakeResponse(200, {"commit": {"sha": "new-commit"}}),
    )
    client.update_file(
        path="docs/API.md",
        content="new",
        branch="feature",
        message="msg",
    )
    assert session.calls[-1].json_body["sha"] == "fetched-sha"


# ---------------------------------------------------------------------------
# create_pull_request / find_open_pr
# ---------------------------------------------------------------------------


def test_create_pull_request_posts_expected_payload(client, session):
    session.queue(FakeResponse(201, {"html_url": "https://example/pr", "number": 7}))
    result = client.create_pull_request(
        base="main", head="feature", title="T", body="B"
    )
    assert result["number"] == 7
    assert session.calls[-1].json_body == {
        "title": "T",
        "head": "feature",
        "base": "main",
        "body": "B",
        "draft": False,
    }


def test_find_open_pr_returns_first_match(client, session):
    session.queue(
        FakeResponse(
            200,
            [{"number": 12, "html_url": "https://example/12"}],
        )
    )
    pr = client.find_open_pr("feature")
    assert pr is not None
    assert pr["number"] == 12
    # Correct head filter was sent
    assert session.calls[-1].params == {
        "head": "octocat:feature",
        "state": "open",
    }


def test_find_open_pr_returns_none_when_empty(client, session):
    session.queue(FakeResponse(200, []))
    assert client.find_open_pr("feature") is None


# ---------------------------------------------------------------------------
# Error translation
# ---------------------------------------------------------------------------


def test_non_2xx_raises_github_api_error_with_status(client, session):
    session.queue(FakeResponse(422, {"message": "Validation Failed"}))
    with pytest.raises(GitHubAPIError) as exc_info:
        client.create_pull_request(base="main", head="x", title="t", body="b")
    assert exc_info.value.status_code == 422
    assert "Validation Failed" in str(exc_info.value)


def test_non_2xx_with_no_json_uses_text(client, session):
    session.queue(FakeResponse(500, body=None))
    with pytest.raises(GitHubAPIError) as exc_info:
        client.get_default_branch()
    assert exc_info.value.status_code == 500
