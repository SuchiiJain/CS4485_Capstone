"""
Patch Generator — produce deterministic doc patches from Docrot flags.

Given a flag (structural change detected by the scanner) and the current
contents of the affected documentation file, this module returns a
modified version of the doc with the change applied.

The patches here are rule-based, not AI-generated. They use the
before/after structural data that the scanner already captures (function
name, signature, parameters, return type) to rewrite matching sections
of the markdown doc.

Supported flag reasons:
    - signature_changed: rewrite the function signature wherever it
      appears in fenced code blocks inside the doc
    - parameter_added / parameter_removed / parameter_renamed: update the
      signature line and annotate prose references to removed or renamed
      params with a TODO marker
    - return_type_changed: update the return type in code blocks and
      annotate prose mentions of the old return type
    - symbol_removed: add a TODO marker above any section referencing
      the removed symbol so the user can decide whether to delete it

Any unsupported reason returns None so callers can fall back to
AI-generated suggestions for that flag.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# Public result types
# ---------------------------------------------------------------------------


@dataclass
class DocPatch:
    """A generated patch for a single documentation file."""

    doc_path: str
    original_content: str
    patched_content: str
    reason: str
    symbol: str
    summary: str
    todo_notes: List[str] = field(default_factory=list)

    @property
    def is_noop(self) -> bool:
        """True when the generator could not confidently rewrite anything."""
        return self.original_content == self.patched_content


# ---------------------------------------------------------------------------
# Markdown utilities
# ---------------------------------------------------------------------------


FENCE_PATTERN = re.compile(
    r"(?P<fence>```(?P<lang>[a-zA-Z0-9_+-]*)\s*\n)(?P<body>.*?)(?P<close>\n```)",
    re.DOTALL,
)


def _iter_code_blocks(content: str):
    """Yield (match, lang, body) tuples for every fenced code block."""
    for match in FENCE_PATTERN.finditer(content):
        yield match, match.group("lang"), match.group("body")


def _replace_code_block_body(content: str, match: re.Match, new_body: str) -> str:
    """Return content with a specific code block's body replaced."""
    start = match.start()
    end = match.end()
    rebuilt = (
        content[:start]
        + match.group("fence")
        + new_body
        + match.group("close")
        + content[end:]
    )
    return rebuilt


def _signature_regex_for(symbol: str) -> re.Pattern:
    """Regex that matches a full `def symbol(...)[:|->]` signature line."""
    escaped = re.escape(symbol)
    # Non-greedy match for the argument list, then optional return type
    return re.compile(
        rf"(?:async\s+)?def\s+{escaped}\s*\([^)]*\)(?:\s*->\s*[^:\n]+)?\s*:?",
        re.MULTILINE,
    )


def _inline_symbol_regex_for(symbol: str) -> re.Pattern:
    """Regex that matches `symbol` in prose when wrapped in backticks."""
    escaped = re.escape(symbol)
    return re.compile(rf"`{escaped}(?:\([^`)]*\))?`")


# ---------------------------------------------------------------------------
# Signature construction
# ---------------------------------------------------------------------------


def _format_param(param: dict) -> str:
    """Render a param dict as a python-style argument."""
    name = param.get("name", "")
    annotation = param.get("annotation") or param.get("type")
    default = param.get("default")

    rendered = name
    if annotation:
        rendered = f"{rendered}: {annotation}"
    if default is not None and default != "":
        rendered = f"{rendered} = {default}"
    return rendered


def _build_signature_line(
    symbol: str,
    params: List[dict],
    return_type: Optional[str],
) -> str:
    """Construct a `def symbol(params) -> return_type:` line."""
    rendered_params = ", ".join(_format_param(p) for p in params if p.get("name"))
    header = f"def {symbol}({rendered_params})"
    if return_type:
        header = f"{header} -> {return_type}"
    return f"{header}:"


def _fallback_signature(flag: dict) -> Optional[str]:
    """Use the flag's stored `signature` field if present, else rebuild."""
    signature = flag.get("signature")
    if signature and isinstance(signature, str):
        trimmed = signature.strip()
        if trimmed.startswith("def "):
            return trimmed if trimmed.endswith(":") else f"{trimmed}:"
    symbol = flag.get("symbol")
    if not symbol:
        return None
    params = flag.get("params") or []
    return_type = flag.get("return_type")
    return _build_signature_line(symbol, params, return_type)


# ---------------------------------------------------------------------------
# Patch strategies
# ---------------------------------------------------------------------------


def _patch_signature(
    content: str,
    symbol: str,
    new_signature_line: str,
) -> Tuple[str, int]:
    """
    Replace every occurrence of `def symbol(...)` inside python code blocks.
    Returns (patched, count) where count is the number of replacements.
    """
    pattern = _signature_regex_for(symbol)
    total_replacements = 0

    patched = content
    replacements: List[Tuple[re.Match, str]] = []
    for match, lang, body in _iter_code_blocks(content):
        if lang and lang.lower() not in {"python", "py", ""}:
            continue
        new_body, count = pattern.subn(new_signature_line, body)
        if count > 0:
            replacements.append((match, new_body))
            total_replacements += count

    # Apply replacements in reverse to keep offsets valid
    for match, new_body in reversed(replacements):
        patched = _replace_code_block_body(patched, match, new_body)

    return patched, total_replacements


def _annotate_prose_mentions(
    content: str,
    symbol: str,
    note: str,
) -> Tuple[str, int]:
    """
    Find inline `symbol` mentions in prose (outside code blocks) and append
    a TODO marker on the same line the first time each is seen. We only
    annotate lines that are NOT inside a fenced code block.
    """
    lines = content.splitlines(keepends=True)
    inside_fence = False
    annotated_count = 0
    seen_lines: set = set()

    pattern = _inline_symbol_regex_for(symbol)

    for idx, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("```"):
            inside_fence = not inside_fence
            continue
        if inside_fence:
            continue
        if pattern.search(line) and idx not in seen_lines:
            # Append annotation at end of line, preserving trailing newline
            if line.endswith("\n"):
                lines[idx] = line.rstrip("\n") + f"  <!-- docrot: {note} -->\n"
            else:
                lines[idx] = line + f"  <!-- docrot: {note} -->"
            annotated_count += 1
            seen_lines.add(idx)

    return "".join(lines), annotated_count


def _patch_symbol_removed(
    content: str,
    symbol: str,
) -> Tuple[str, List[str]]:
    """
    Mark every section referencing a removed symbol with a TODO note,
    since we cannot safely decide to delete text on the user's behalf.
    """
    note = f"removed symbol `{symbol}` — consider deleting this section"
    patched, count = _annotate_prose_mentions(content, symbol, note)
    notes = []
    if count > 0:
        notes.append(
            f"Annotated {count} prose reference(s) to removed symbol "
            f"`{symbol}`. Review and delete as appropriate."
        )
    return patched, notes


def _patch_return_type(
    content: str,
    symbol: str,
    new_signature_line: str,
    new_return_type: Optional[str],
) -> Tuple[str, List[str]]:
    """Update return type in code blocks + annotate prose that describes it."""
    patched, sig_count = _patch_signature(content, symbol, new_signature_line)
    notes: List[str] = []
    if sig_count > 0:
        notes.append(
            f"Updated return type in {sig_count} code block signature(s) "
            f"for `{symbol}`."
        )
    if new_return_type:
        note = f"return type for `{symbol}` is now `{new_return_type}`"
        patched, prose_count = _annotate_prose_mentions(patched, symbol, note)
        if prose_count > 0:
            notes.append(
                f"Annotated {prose_count} prose reference(s) that may describe "
                f"the old return type."
            )
    return patched, notes


def _patch_parameters(
    content: str,
    flag: dict,
    new_signature_line: str,
) -> Tuple[str, List[str]]:
    """Update the signature line and optionally annotate renamed params."""
    symbol = flag.get("symbol", "")
    patched, sig_count = _patch_signature(content, symbol, new_signature_line)
    notes: List[str] = []
    if sig_count > 0:
        notes.append(
            f"Updated signature in {sig_count} code block(s) for `{symbol}`."
        )

    reason = flag.get("reason", "")
    removed_param = flag.get("removed_param") or flag.get("old_param_name")
    renamed_from = flag.get("renamed_from") or flag.get("old_param_name")
    renamed_to = flag.get("renamed_to") or flag.get("new_param_name")

    if reason == "parameter_removed" and removed_param:
        note = f"parameter `{removed_param}` was removed from `{symbol}`"
        patched, n = _annotate_prose_mentions(patched, removed_param, note)
        if n > 0:
            notes.append(
                f"Annotated {n} prose mention(s) of removed parameter "
                f"`{removed_param}`."
            )
    elif reason == "parameter_renamed" and renamed_from and renamed_to:
        note = (
            f"parameter `{renamed_from}` renamed to `{renamed_to}` in `{symbol}`"
        )
        patched, n = _annotate_prose_mentions(patched, renamed_from, note)
        if n > 0:
            notes.append(
                f"Annotated {n} prose mention(s) of renamed parameter "
                f"`{renamed_from}` → `{renamed_to}`."
            )

    return patched, notes


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


SUPPORTED_REASONS = {
    "signature_changed",
    "parameter_added",
    "parameter_removed",
    "parameter_renamed",
    "return_type_changed",
    "symbol_removed",
}


def generate_patch(flag: dict, doc_content: str) -> Optional[DocPatch]:
    """
    Generate a DocPatch for the given flag and doc content.

    Returns None when the flag is missing required data or its reason is
    not supported by the deterministic patch engine (in which case the
    caller should fall back to AI suggestions).

    Args:
        flag: Dict representation of a Flag as stored in Firestore. Must
            include `reason`, `symbol`, and `doc_file`. Signature data
            (`signature`, `params`, `return_type`) is required for most
            structural reasons.
        doc_content: Current text of the doc file.

    Returns:
        DocPatch describing the rewrite, or None.
    """
    reason = flag.get("reason", "")
    symbol = flag.get("symbol", "")
    doc_path = flag.get("doc_file", "")

    if not reason or not symbol or not doc_path:
        return None
    if reason not in SUPPORTED_REASONS:
        return None

    new_signature = _fallback_signature(flag) or ""
    summary_parts: List[str] = []
    todo_notes: List[str] = []
    patched = doc_content

    if reason == "signature_changed":
        if not new_signature:
            return None
        patched, count = _patch_signature(patched, symbol, new_signature)
        if count == 0:
            return None
        summary_parts.append(
            f"Updated signature for `{symbol}` in {count} code block(s)."
        )

    elif reason in {"parameter_added", "parameter_removed", "parameter_renamed"}:
        if not new_signature:
            return None
        patched, notes = _patch_parameters(patched, flag, new_signature)
        if patched == doc_content and not notes:
            return None
        todo_notes.extend(notes)
        summary_parts.extend(notes)

    elif reason == "return_type_changed":
        if not new_signature:
            return None
        patched, notes = _patch_return_type(
            patched, symbol, new_signature, flag.get("return_type")
        )
        if patched == doc_content and not notes:
            return None
        todo_notes.extend(notes)
        summary_parts.extend(notes)

    elif reason == "symbol_removed":
        patched, notes = _patch_symbol_removed(patched, symbol)
        if patched == doc_content:
            return None
        todo_notes.extend(notes)
        summary_parts.extend(notes)

    else:  # defensive: already filtered by SUPPORTED_REASONS
        return None

    if not summary_parts:
        summary_parts.append(f"Applied `{reason}` fix for `{symbol}`.")

    return DocPatch(
        doc_path=doc_path,
        original_content=doc_content,
        patched_content=patched,
        reason=reason,
        symbol=symbol,
        summary=" ".join(summary_parts),
        todo_notes=todo_notes,
    )


def describe_unsupported(flag: dict) -> str:
    """Human-readable explanation for flags the patch generator skips."""
    reason = flag.get("reason", "unknown")
    symbol = flag.get("symbol", "?")
    if reason not in SUPPORTED_REASONS:
        return (
            f"Reason `{reason}` for `{symbol}` is not handled by the deterministic "
            f"patch generator. Fall back to the AI suggestion for this flag."
        )
    return f"Patch for `{symbol}` ({reason}) could not be generated."
