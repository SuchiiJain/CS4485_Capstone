"""Tests for the GitHub PR comment formatter (CS4485-50).

The formatter reads `.docrot-report.json` and produces the Markdown body
posted on the PR. Prior to CS4485-50 it only showed `message` and
`suggestion` per flag — reviewers had no way to see WHICH source or doc
file was affected without opening the raw JSON report.

These tests pin the new behavior: every flag section must surface the
affected source file + symbol, and (when present) the documentation
file and referenced doc symbol.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from src.github_integration import format_pr_comment


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_flag(
    severity: str,
    *,
    message: str = "docstring is stale",
    suggestion: str = "Update the docstring.",
    code_file: str = "src/run.py",
    symbol: str = "run",
    doc_file: str | None = "docs/API.md",
    referenced_symbol: str | None = "run",
) -> dict:
    flag = {
        "reason": "docstring_stale",
        "severity": severity,
        "code_element": {
            "name": symbol,
            "file_path": code_file,
            "signature": f"def {symbol}(x):",
            "params": [],
            "return_type": None,
        },
        "message": message,
        "suggestion": suggestion,
    }
    if doc_file is not None:
        flag["doc_reference"] = {
            "file_path": doc_file,
            "referenced_symbol": referenced_symbol,
            "snippet": "",
        }
    else:
        flag["doc_reference"] = None
    return flag


def _write_report(tmp_path: Path, flags: list[dict], ai_suggestions=None) -> str:
    data = {
        "meta": {
            "repo_path": "octocat/hello-world",
            "commit_hash": "deadbeefcafebabe",
            "timestamp": "2026-04-14T00:00:00",
            "total_issues": len(flags),
            "severity_summary": {
                "high": sum(1 for f in flags if f["severity"] == "high"),
                "medium": sum(1 for f in flags if f["severity"] == "medium"),
                "low": sum(1 for f in flags if f["severity"] == "low"),
            },
        },
        "issues": flags,
    }
    if ai_suggestions:
        data["ai_suggestions"] = ai_suggestions
    path = tmp_path / ".docrot-report.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


# ---------------------------------------------------------------------------
# Early returns
# ---------------------------------------------------------------------------


def test_returns_none_when_report_missing(tmp_path):
    missing = tmp_path / "nope.json"
    assert format_pr_comment(str(missing), "abc") is None


def test_returns_none_when_report_has_no_flags(tmp_path):
    report = _write_report(tmp_path, [])
    assert format_pr_comment(report, "abc") is None


def test_returns_none_for_corrupt_json(tmp_path):
    path = tmp_path / ".docrot-report.json"
    path.write_text("{not valid json", encoding="utf-8")
    assert format_pr_comment(str(path), "abc") is None


# ---------------------------------------------------------------------------
# CS4485-50 — affected file surfacing
# ---------------------------------------------------------------------------


def test_high_severity_flag_surfaces_source_and_doc_paths(tmp_path):
    report = _write_report(
        tmp_path,
        [_make_flag("high", code_file="src/run.py", symbol="run", doc_file="docs/API.md")],
    )
    body = format_pr_comment(report, "deadbeef")
    assert body is not None
    assert "High Severity" in body
    # Source path should now appear under the flag bullet
    assert "_Source:_" in body
    assert "src/run.py" in body
    assert "`run`" in body
    # And the affected doc file
    assert "_Affected doc:_" in body
    assert "docs/API.md" in body


def test_medium_severity_flag_also_gets_location_lines(tmp_path):
    report = _write_report(
        tmp_path,
        [_make_flag("medium", code_file="src/comparator.py", symbol="compare", doc_file="docs/Architecture.md")],
    )
    body = format_pr_comment(report, "cafebabe")
    assert body is not None
    assert "Medium Severity" in body
    assert "src/comparator.py" in body
    assert "docs/Architecture.md" in body


def test_low_severity_flag_gets_location_lines(tmp_path):
    report = _write_report(
        tmp_path,
        [_make_flag("low", code_file="src/alerts.py", symbol="notify", doc_file="docs/README.md")],
    )
    body = format_pr_comment(report, "abc")
    assert body is not None
    assert "Low Severity" in body
    assert "src/alerts.py" in body
    assert "docs/README.md" in body


def test_flag_without_doc_reference_still_shows_source(tmp_path):
    report = _write_report(
        tmp_path,
        [_make_flag("high", code_file="src/run.py", symbol="run", doc_file=None)],
    )
    body = format_pr_comment(report, "abc")
    assert body is not None
    # Source is present
    assert "src/run.py" in body
    # But no "Affected doc" line since doc_reference was null
    assert "_Affected doc:_" not in body


def test_doc_reference_includes_referenced_symbol_when_present(tmp_path):
    report = _write_report(
        tmp_path,
        [
            _make_flag(
                "high",
                code_file="src/run.py",
                symbol="run",
                doc_file="docs/API.md",
                referenced_symbol="run",
            )
        ],
    )
    body = format_pr_comment(report, "abc")
    assert body is not None
    assert "referenced symbol: `run`" in body


# ---------------------------------------------------------------------------
# Regression guards — existing behavior kept
# ---------------------------------------------------------------------------


def test_severity_counts_table_still_rendered(tmp_path):
    report = _write_report(
        tmp_path,
        [
            _make_flag("high"),
            _make_flag("medium"),
            _make_flag("low"),
        ],
    )
    body = format_pr_comment(report, "abc")
    assert body is not None
    assert "| Severity | Count |" in body
    assert "3 alert(s) found" in body


def test_commit_sha_shortened_to_8_chars(tmp_path):
    report = _write_report(tmp_path, [_make_flag("high")])
    body = format_pr_comment(report, "deadbeefcafebabe")
    assert body is not None
    assert "`deadbeef`" in body
    assert "cafebabe" not in body  # only the 8-char prefix should appear


def test_message_and_suggestion_still_rendered(tmp_path):
    report = _write_report(
        tmp_path,
        [
            _make_flag(
                "high",
                message="docstring drift detected",
                suggestion="Rewrite the docstring for run().",
            )
        ],
    )
    body = format_pr_comment(report, "abc")
    assert body is not None
    assert "docstring drift detected" in body
    assert "Rewrite the docstring for run()." in body


def test_ai_suggestions_section_rendered_when_present(tmp_path):
    report = _write_report(
        tmp_path,
        [_make_flag("high")],
        ai_suggestions=[
            {
                "doc_path": "docs/API.md",
                "triggered_by": ["run"],
                "suggestion": "Regenerate the examples block.",
                "model_used": "claude-opus",
            }
        ],
    )
    body = format_pr_comment(report, "abc")
    assert body is not None
    assert "AI-Generated Suggestions" in body
    assert "Regenerate the examples block." in body
    assert "claude-opus" in body
