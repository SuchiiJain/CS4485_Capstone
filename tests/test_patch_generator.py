"""Tests for the deterministic doc patch generator.

These tests pin behavior for every supported flag reason:
    - signature_changed
    - parameter_added / parameter_removed / parameter_renamed
    - return_type_changed
    - symbol_removed

They also cover the edge cases that make or break a patch:
    - code-block-only rewrites (prose is left alone except for annotation)
    - non-Python fenced blocks are ignored
    - prose mentions outside fences get a TODO annotation
    - unsupported reasons return None
    - a patch that produces zero changes is marked as a no-op
"""

from __future__ import annotations

import textwrap

import pytest

from src.patch_generator import (
    DocPatch,
    SUPPORTED_REASONS,
    describe_unsupported,
    generate_patch,
)


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _md(*blocks: str) -> str:
    """Join markdown blocks separated by blank lines, trimming indentation."""
    return "\n\n".join(textwrap.dedent(b).strip("\n") for b in blocks) + "\n"


def _signature_flag(
    *,
    symbol: str = "format_user",
    doc_file: str = "docs/API.md",
    signature: str = "def format_user(user: User, verbose: bool = False) -> str:",
    params=None,
    return_type: str = "str",
    reason: str = "signature_changed",
) -> dict:
    return {
        "reason": reason,
        "symbol": symbol,
        "doc_file": doc_file,
        "signature": signature,
        "params": params
        or [
            {"name": "user", "annotation": "User"},
            {"name": "verbose", "annotation": "bool", "default": "False"},
        ],
        "return_type": return_type,
    }


# ---------------------------------------------------------------------------
# Constants / metadata
# ---------------------------------------------------------------------------


def test_supported_reasons_is_the_complete_handled_set():
    assert SUPPORTED_REASONS == {
        "signature_changed",
        "parameter_added",
        "parameter_removed",
        "parameter_renamed",
        "return_type_changed",
        "symbol_removed",
    }


# ---------------------------------------------------------------------------
# signature_changed
# ---------------------------------------------------------------------------


def test_signature_changed_rewrites_python_fence_only():
    doc = _md(
        "# API",
        """
        ```python
        def format_user(user):
            ...
        ```
        """,
        """
        ```bash
        def format_user(user):  # should NOT be rewritten
        ```
        """,
    )
    patch = generate_patch(_signature_flag(), doc)

    assert isinstance(patch, DocPatch)
    assert not patch.is_noop
    assert "def format_user(user: User, verbose: bool = False) -> str:" in patch.patched_content
    # Non-python fence stays verbatim
    assert "def format_user(user):  # should NOT be rewritten" in patch.patched_content


def test_signature_changed_requires_a_match_in_a_code_block():
    doc = _md("# API", "No code here, just prose referencing `format_user`.")
    assert generate_patch(_signature_flag(), doc) is None


def test_signature_changed_handles_async_def():
    doc = _md(
        """
        ```python
        async def format_user(user):
            ...
        ```
        """
    )
    patch = generate_patch(_signature_flag(), doc)
    assert patch is not None
    assert "def format_user(user: User, verbose: bool = False) -> str:" in patch.patched_content


def test_signature_changed_rewrites_multiple_code_blocks():
    doc = _md(
        """
        ```python
        def format_user(user):
            ...
        ```
        """,
        "And another example:",
        """
        ```py
        def format_user(u):
            pass
        ```
        """,
    )
    patch = generate_patch(_signature_flag(), doc)
    assert patch is not None
    count = patch.patched_content.count(
        "def format_user(user: User, verbose: bool = False) -> str:"
    )
    assert count == 2


# ---------------------------------------------------------------------------
# parameter_added / removed / renamed
# ---------------------------------------------------------------------------


def test_parameter_added_updates_signature_in_code():
    flag = _signature_flag(reason="parameter_added")
    doc = _md(
        """
        ```python
        def format_user(user):
            ...
        ```
        """
    )
    patch = generate_patch(flag, doc)
    assert patch is not None
    assert "verbose: bool = False" in patch.patched_content


def test_parameter_removed_annotates_prose_mentions():
    flag = {
        "reason": "parameter_removed",
        "symbol": "format_user",
        "doc_file": "docs/API.md",
        "signature": "def format_user(user: User) -> str:",
        "params": [{"name": "user", "annotation": "User"}],
        "return_type": "str",
        "removed_param": "verbose",
    }
    doc = _md(
        """
        ```python
        def format_user(user, verbose=False):
            ...
        ```
        """,
        "Set the `verbose` flag to enable extra logging.",
    )
    patch = generate_patch(flag, doc)
    assert patch is not None
    assert "def format_user(user: User) -> str:" in patch.patched_content
    assert "<!-- docrot:" in patch.patched_content
    assert any("verbose" in n for n in patch.todo_notes)


def test_parameter_renamed_annotates_old_name_in_prose():
    flag = {
        "reason": "parameter_renamed",
        "symbol": "format_user",
        "doc_file": "docs/API.md",
        "signature": "def format_user(account: User) -> str:",
        "params": [{"name": "account", "annotation": "User"}],
        "return_type": "str",
        "renamed_from": "user",
        "renamed_to": "account",
    }
    doc = _md(
        """
        ```python
        def format_user(user):
            ...
        ```
        """,
        "Pass a populated `user` object.",
    )
    patch = generate_patch(flag, doc)
    assert patch is not None
    assert "def format_user(account: User) -> str:" in patch.patched_content
    assert "renamed to `account`" in patch.patched_content or "<!-- docrot:" in patch.patched_content


# ---------------------------------------------------------------------------
# return_type_changed
# ---------------------------------------------------------------------------


def test_return_type_changed_updates_signature_and_notes_prose():
    flag = _signature_flag(
        reason="return_type_changed",
        signature="def format_user(user: User, verbose: bool = False) -> dict:",
        return_type="dict",
    )
    doc = _md(
        """
        ```python
        def format_user(user, verbose=False):
            ...
        ```
        """,
        "`format_user` returns a formatted string.",
    )
    patch = generate_patch(flag, doc)
    assert patch is not None
    assert "-> dict:" in patch.patched_content
    # Prose mention should have gotten annotated
    assert "<!-- docrot:" in patch.patched_content


# ---------------------------------------------------------------------------
# symbol_removed
# ---------------------------------------------------------------------------


def test_symbol_removed_annotates_prose_sections():
    flag = {
        "reason": "symbol_removed",
        "symbol": "legacy_helper",
        "doc_file": "docs/API.md",
    }
    doc = _md(
        "# API",
        "Call `legacy_helper` when you need the old-style formatting.",
        "Unrelated line.",
    )
    patch = generate_patch(flag, doc)
    assert patch is not None
    assert "<!-- docrot:" in patch.patched_content
    assert "legacy_helper" in patch.summary


def test_symbol_removed_without_mentions_is_noop_and_returns_none():
    flag = {
        "reason": "symbol_removed",
        "symbol": "never_referenced",
        "doc_file": "docs/API.md",
    }
    doc = _md("# API", "Nothing references the removed symbol here.")
    assert generate_patch(flag, doc) is None


# ---------------------------------------------------------------------------
# Validation / unsupported paths
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "flag",
    [
        {},
        {"reason": "signature_changed"},
        {"reason": "signature_changed", "symbol": "foo"},
        {"symbol": "foo", "doc_file": "d.md"},
    ],
)
def test_generate_patch_requires_core_fields(flag):
    assert generate_patch(flag, "anything") is None


def test_generate_patch_rejects_unsupported_reason():
    flag = {
        "reason": "docstring_stale",
        "symbol": "foo",
        "doc_file": "docs/API.md",
    }
    assert generate_patch(flag, "...") is None


def test_describe_unsupported_mentions_reason_and_symbol():
    flag = {"reason": "docstring_stale", "symbol": "foo"}
    message = describe_unsupported(flag)
    assert "docstring_stale" in message
    assert "foo" in message


def test_describe_unsupported_supported_reason_returns_generic_message():
    flag = {"reason": "signature_changed", "symbol": "foo"}
    message = describe_unsupported(flag)
    assert "foo" in message
    assert "signature_changed" in message


# ---------------------------------------------------------------------------
# DocPatch wrapper
# ---------------------------------------------------------------------------


def test_docpatch_is_noop_property():
    same = DocPatch(
        doc_path="x.md",
        original_content="hi",
        patched_content="hi",
        reason="signature_changed",
        symbol="foo",
        summary="",
    )
    assert same.is_noop is True

    changed = DocPatch(
        doc_path="x.md",
        original_content="hi",
        patched_content="bye",
        reason="signature_changed",
        symbol="foo",
        summary="",
    )
    assert changed.is_noop is False
