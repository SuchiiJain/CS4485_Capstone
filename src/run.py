"""
run.py — Documentation Rot Detector entry point.

Usage:
    python run.py [repo_path] [--commit <hash>]

If repo_path is omitted, the current working directory is used.

Pipeline:
    1. Load config (.docrot-config.json)
    2. Scan all Python source files → extract FunctionFingerprints (ast_parser)
    3. First run → save baseline, exit with no alerts
    4. Subsequent runs → compare against stored baseline (comparator)
    5. Score semantic deltas → ChangeEvents → DocAlerts (alerts)
    6. Bridge ChangeEvents into flagging_threshold.Flag objects
    7. Generate .docrot-report.txt + .docrot-report.json (report_generation)
    8. Print report to stdout and update stored fingerprints
"""

import os
import sys
import time
import argparse
from typing import Dict, List, Optional

# FIX: All files are in the same flat directory — no 'src.' prefix needed.
from ast_parser import extract_function_fingerprints
from comparator import compare_file_functions
from alerts import (
    evaluate_doc_flags,
    publish_alerts_to_log,
    publish_alerts_to_report,
    publish_baseline_notice,
)
from config import load_config, get_doc_mappings, get_thresholds
from models import ChangeEvent, DocAlert, FunctionFingerprint
from persistence import (
    is_first_run,
    load_fingerprints,
    persist_fingerprints,
    serialize_file_fingerprints,
    deserialize_file_fingerprints,
    update_fingerprint_baseline,
)

from src.flagging_threshold import (
    CodeElement,
    DocReference,
    Flag,
    FlagReason,
    Severity,
    run_flagging,
)
from src.report_generation import generate_reports


# ---------------------------------------------------------------------------
# Repo scanning helpers
# ---------------------------------------------------------------------------

_SKIP_DIRS = {
    ".git", "__pycache__", ".venv", "venv", "node_modules",
    ".tox", "dist", "build",
}


def _collect_python_files(repo_path: str) -> List[str]:
    """Walk the repo and return all .py paths relative to repo_path."""
    py_files: List[str] = []
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS and not d.startswith(".")]
        for filename in files:
            if filename.endswith(".py"):
                abs_path = os.path.join(root, filename)
                rel_path = os.path.relpath(abs_path, repo_path).replace("\\", "/")
                py_files.append(rel_path)
    return sorted(py_files)


def _read_source(repo_path: str, rel_path: str) -> Optional[str]:
    """Read a source file; return None on error."""
    abs_path = os.path.join(repo_path, rel_path)
    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError as e:
        print(f"[docrot] Warning: could not read {rel_path}: {e}")
        return None


def _scan_repo(
    repo_path: str, py_files: List[str]
) -> tuple[Dict[str, Dict[str, FunctionFingerprint]], List[str]]:
    """
    Return ({rel_file_path: {stable_id: FunctionFingerprint}}, failed_files)
    for every .py file. Files that fail to read are tracked separately so
    we can avoid clobbering their stored fingerprints.
    """
    all_fps: Dict[str, Dict[str, FunctionFingerprint]] = {}
    failed_files: List[str] = []
    for rel_path in py_files:
        source = _read_source(repo_path, rel_path)
        if source is None:
            failed_files.append(rel_path)
            continue
        file_fps = extract_function_fingerprints(source, rel_path)
        if file_fps:
            all_fps[rel_path] = file_fps
    return all_fps, failed_files


# ---------------------------------------------------------------------------
# Bridge: FunctionFingerprint → CodeElement
# ---------------------------------------------------------------------------

def _fp_to_code_element(fp: FunctionFingerprint) -> CodeElement:
    """
    Convert a FunctionFingerprint into a CodeElement for flagging_threshold.

    The stable_id is used as the element name so both systems share the
    same key space (file::Class.method or file::function).
    """
    param_str = ", ".join(fp.signature.params)
    ret = fp.signature.return_annotation or ""
    signature_str = f"{fp.signature.name}({param_str}){' -> ' + ret if ret else ''}"

    return CodeElement(
        name=fp.stable_id,
        file_path=fp.file_path,
        signature=signature_str,
        hash=fp.fingerprint_hash,
        params=fp.signature.params,
        return_type=fp.signature.return_annotation,
        docstring=None,   # Not available in FunctionFingerprint at this stage
    )


# ---------------------------------------------------------------------------
# Bridge: ChangeEvent → Flag
# ---------------------------------------------------------------------------

# Map ChangeEvent reason strings to FlagReason enum values.
# NOTE: "function added" (bare) is never emitted by comparator.py — only
# "function added (public API)" is used. The bare key is kept for safety
# but will not be matched in practice.
_REASON_MAP: Dict[str, FlagReason] = {
    "public signature changed":        FlagReason.SIGNATURE_CHANGED,
    "default argument changed":        FlagReason.SIGNATURE_CHANGED,
    "return behavior changed":         FlagReason.RETURN_TYPE_CHANGED,
    "side-effect behavior changed":    FlagReason.DOCSTRING_STALE,
    "auth/permission logic changed":   FlagReason.DOCSTRING_STALE,
    "exception behavior changed":      FlagReason.DOCSTRING_STALE,
    "core control path added/removed": FlagReason.DOCSTRING_STALE,
    "branch condition changed":        FlagReason.DOCSTRING_STALE,
    "loop behavior changed":           FlagReason.DOCSTRING_STALE,
    "literal/constant changed":        FlagReason.DOCSTRING_STALE,
    "function added (public API)":     FlagReason.SIGNATURE_CHANGED,
    "function added":                  FlagReason.DOCSTRING_MISSING,
    "function removed (public API)":   FlagReason.SYMBOL_REMOVED,
    "function removed":                FlagReason.SYMBOL_REMOVED,
    "public API added/removed":        FlagReason.SYMBOL_REMOVED,
}

_SEVERITY_FROM_REASON: Dict[FlagReason, Severity] = {
    FlagReason.SIGNATURE_CHANGED:   Severity.HIGH,
    FlagReason.SYMBOL_REMOVED:      Severity.HIGH,
    FlagReason.MARKDOWN_REF_BROKEN: Severity.HIGH,
    FlagReason.RETURN_TYPE_CHANGED: Severity.MEDIUM,
    FlagReason.PARAMETER_ADDED:     Severity.MEDIUM,
    FlagReason.PARAMETER_REMOVED:   Severity.MEDIUM,
    FlagReason.DOCSTRING_STALE:     Severity.MEDIUM,
    FlagReason.PARAMETER_RENAMED:   Severity.LOW,
    FlagReason.DOCSTRING_MISSING:   Severity.LOW,
}


def _make_suggestion(reason: FlagReason, fn_id: str) -> str:
    suggestions = {
        FlagReason.SIGNATURE_CHANGED:   f"Update documentation for '{fn_id}' to reflect the new signature.",
        FlagReason.SYMBOL_REMOVED:      f"Remove or replace documentation references to '{fn_id}'.",
        FlagReason.RETURN_TYPE_CHANGED: f"Update the return type description for '{fn_id}' in documentation.",
        FlagReason.PARAMETER_ADDED:     f"Document the new parameters added to '{fn_id}'.",
        FlagReason.PARAMETER_REMOVED:   f"Remove documentation for parameters deleted from '{fn_id}'.",
        FlagReason.DOCSTRING_STALE:     f"Review documentation for '{fn_id}' — logic may have changed.",
        FlagReason.DOCSTRING_MISSING:   f"Add a docstring to the new public function '{fn_id}'.",
        FlagReason.MARKDOWN_REF_BROKEN: f"Fix or remove markdown references to '{fn_id}'.",
        FlagReason.PARAMETER_RENAMED:   f"Update parameter names for '{fn_id}' in documentation.",
    }
    return suggestions.get(reason, f"Review documentation related to '{fn_id}'.")


def _change_events_to_flags(
    events: List[ChangeEvent],
    old_fps: Dict[str, Dict[str, FunctionFingerprint]],
    new_fps: Dict[str, Dict[str, FunctionFingerprint]],
) -> List[Flag]:
    """
    Convert ChangeEvents from the comparator into Flag objects expected by
    report_generation.

    For each event we pick the best matching FlagReason from the event's
    reasons list, then build a Flag with the appropriate severity.
    """
    flags: List[Flag] = []

    for event in events:
        # Resolve best flag reason from the event's reasons list
        flag_reason = FlagReason.DOCSTRING_STALE  # default fallback
        for r in event.reasons:
            if r in _REASON_MAP:
                flag_reason = _REASON_MAP[r]
                break

        severity = Severity.HIGH if event.critical else _SEVERITY_FROM_REASON.get(
            flag_reason, Severity.MEDIUM
        )

        # Resolve the CodeElement — prefer new fingerprint, fall back to old
        fp = (
            new_fps.get(event.code_path, {}).get(event.function_id)
            or old_fps.get(event.code_path, {}).get(event.function_id)
        )

        if fp:
            code_elem = _fp_to_code_element(fp)
        else:
            code_elem = CodeElement(
                name=event.function_id,
                file_path=event.code_path,
                signature="",
                hash="",
                params=[],
                return_type=None,
                docstring=None,
            )

        message = (
            f"[{flag_reason.value}] '{event.function_id}' — "
            f"{', '.join(event.reasons)} (score: {event.score})"
        )

        flags.append(Flag(
            reason=flag_reason,
            severity=severity,
            code_element=code_elem,
            doc_reference=None,
            message=message,
            suggestion=_make_suggestion(flag_reason, event.function_id),
        ))

    # Sort HIGH → MEDIUM → LOW
    order = {Severity.HIGH: 0, Severity.MEDIUM: 1, Severity.LOW: 2}
    flags.sort(key=lambda f: order[f.severity])
    return flags


# ---------------------------------------------------------------------------
# Bridge: DocAlert → Flag (so doc-file alerts appear in reports)
# ---------------------------------------------------------------------------

def _doc_alerts_to_flags(doc_alerts: List[DocAlert]) -> List[Flag]:
    """
    Convert DocAlert objects into Flag objects so they appear in the
    generated .txt/.json reports, not just in the stdout summary.
    """
    flags: List[Flag] = []
    for alert in doc_alerts:
        severity = Severity.HIGH if alert.critical_found else Severity.MEDIUM
        code_elem = CodeElement(
            name=alert.doc_path,
            file_path=alert.doc_path,
            signature="",
            hash="",
            params=[],
            return_type=None,
            docstring=None,
        )
        flags.append(Flag(
            reason=FlagReason.DOCSTRING_STALE,
            severity=severity,
            code_element=code_elem,
            doc_reference=None,
            message=(
                f"[doc_file_flagged] '{alert.doc_path}' — "
                f"{', '.join(alert.reasons)} (cumulative score: {alert.cumulative_score})"
            ),
            suggestion=f"Review '{alert.doc_path}' — linked code logic has changed.",
        ))
    return flags


# ---------------------------------------------------------------------------
# Stdout report
# ---------------------------------------------------------------------------

def _print_report(
    events: List[ChangeEvent],
    doc_alerts: List[DocAlert],
    flags: List[Flag],
    elapsed: float,
    file_count: int,
    func_count: int,
    report_paths: Dict[str, str],
) -> None:
    """Print a human-readable summary to stdout."""
    SEP = "─" * 64
    print()
    print(SEP)
    print("  Documentation Rot Detector — Scan Report")
    print(SEP)
    print(f"  Files scanned  : {file_count}")
    print(f"  Functions found: {func_count}")
    print(f"  Scan time      : {elapsed:.2f}s")
    print(SEP)

    if not events:
        print("  ✔  No code changes detected since last scan.")
        print(SEP)
        print()
        return

    # ── Function-level changes ────────────────────────────────────────────
    critical = [e for e in events if e.critical]
    minor = [e for e in events if not e.critical]

    print(f"\n  CODE CHANGES  ({len(events)} function(s) changed)\n")
    if critical:
        print(f"  ⚠  Critical ({len(critical)}):")
        for e in critical:
            print(f"     • [{e.event_type}]  {e.function_id}")
            print(f"       Reasons : {', '.join(e.reasons)}")
            print(f"       Score   : {e.score}")
        print()
    if minor:
        print(f"  ℹ  Non-critical ({len(minor)}):")
        for e in minor:
            print(f"     • [{e.event_type}]  {e.function_id}")
            print(f"       Reasons : {', '.join(e.reasons)}")
            print(f"       Score   : {e.score}")
        print()

    print(SEP)

    # ── Doc-file alerts ───────────────────────────────────────────────────
    if doc_alerts:
        print(f"\n  DOCUMENTATION FILES FLAGGED  ({len(doc_alerts)})\n")
        for alert in doc_alerts:
            tag = "⚠  CRITICAL" if alert.critical_found else "ℹ  WARNING"
            print(f"  {tag}: {alert.doc_path}")
            print(f"     Cumulative score : {alert.cumulative_score}")
            print(f"     Reasons          : {', '.join(alert.reasons)}")
            if alert.functions:
                print(f"     Affected funcs   : {', '.join(alert.functions)}")
            print()
    else:
        print("  ✔  No documentation files flagged (scores below threshold).")

    print(SEP)

    # ── Severity summary ──────────────────────────────────────────────────
    counts: Dict[str, int] = {"high": 0, "medium": 0, "low": 0}
    for f in flags:
        counts[f.severity.value] += 1
    print(
        f"\n  SEVERITY SUMMARY  "
        f"High: {counts['high']}  Medium: {counts['medium']}  Low: {counts['low']}"
    )

    # ── Report file paths ─────────────────────────────────────────────────
    if report_paths:
        print(f"\n  Reports written:")
        for fmt, path in report_paths.items():
            print(f"     [{fmt.upper()}]  {path}")

    print(SEP)
    print()


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run(repo_path: str, commit_hash: Optional[str] = None) -> int:
    """
    Execute the full detection pipeline.

    Returns:
        0 = clean, 1 = issues found, 2 = error
    """
    start = time.time()
    repo_path = os.path.abspath(repo_path)

    if not os.path.isdir(repo_path):
        print(f"[docrot] Error: '{repo_path}' is not a valid directory.")
        return 2

    print(f"[docrot] Scanning: {repo_path}")

    # 1. Config
    config = load_config(repo_path)
    doc_mappings = get_doc_mappings(config)
    thresholds = get_thresholds(config)

    if not doc_mappings:
        print(
            "[docrot] Warning: no doc_mappings in .docrot-config.json — "
            "doc-file alerts will not be generated.\n"
            "         Add a 'doc_mappings' section to map source files to docs."
        )

    # 2. Collect + fingerprint
    py_files = _collect_python_files(repo_path)
    if not py_files:
        print("[docrot] No Python files found. Exiting.")
        return 0

    print(f"[docrot] Found {len(py_files)} Python file(s). Extracting fingerprints...")
    # FIX: _scan_repo now also returns a list of files that failed to read,
    # so we can avoid clobbering their stored fingerprints later.
    current_fps, failed_files = _scan_repo(repo_path, py_files)
    total_funcs = sum(len(fps) for fps in current_fps.values())
    print(f"[docrot] Extracted {total_funcs} function fingerprint(s).")
    if failed_files:
        print(f"[docrot] Warning: {len(failed_files)} file(s) could not be read and will be skipped.")

    # 3. First run — save baseline, no alerts
    if is_first_run(repo_path):
        serialized = {
            fp: serialize_file_fingerprints(fps)
            for fp, fps in current_fps.items()
        }
        baseline_stats = update_fingerprint_baseline(repo_path, serialized)
        publish_baseline_notice()
        print(
            "[docrot] Baseline created: "
            f"files={baseline_stats['total_files']} "
            f"functions={baseline_stats['total_functions']}"
        )
        print(f"[docrot] Done in {time.time() - start:.2f}s.")
        return 0

    # 4. Load baseline
    stored_raw = load_fingerprints(repo_path)
    old_fps: Dict[str, Dict[str, FunctionFingerprint]] = {
        fp: deserialize_file_fingerprints(fp_dict)
        for fp, fp_dict in stored_raw.items()
    }

    # 5. Compare → ChangeEvents
    # Only compare files we successfully scanned; skip failed files entirely
    # so their functions don't appear as spuriously removed.
    all_events: List[ChangeEvent] = []
    for file_path in sorted(set(old_fps) | set(current_fps)):
        if file_path in failed_files:
            continue
        events = compare_file_functions(
            old_fps.get(file_path, {}),
            current_fps.get(file_path, {}),
            file_path,
        )
        all_events.extend(events)

    # 6. DocAlerts (alerts.py pipeline — maps events to doc files via config)
    doc_alerts = evaluate_doc_flags(all_events, doc_mappings, thresholds)

    # 7. Flags (flagging_threshold pipeline — richer per-function severity model)
    #    FIX: Also include doc_alerts as flags so they appear in reports.
    flags = _change_events_to_flags(all_events, old_fps, current_fps)
    flags += _doc_alerts_to_flags(doc_alerts)
    order = {Severity.HIGH: 0, Severity.MEDIUM: 1, Severity.LOW: 2}
    flags.sort(key=lambda f: order[f.severity])

    # 8. Generate .txt and .json reports
    elapsed = time.time() - start
    report_paths: Dict[str, str] = {}
    if all_events:
        json_path = os.path.join(repo_path, ".docrot-report.json")
        txt_path = os.path.join(repo_path, ".docrot-report.txt")
        report_paths = generate_reports(
            flags=flags,
            repo_path=repo_path,
            commit_hash=commit_hash,
            json_path=json_path,
            txt_path=txt_path,
        )

    # 9. Print stdout summary
    _print_report(
        all_events, doc_alerts, flags, elapsed,
        len(py_files), total_funcs, report_paths,
    )

    # 10. Persist updated baseline.
    # FIX: Preserve old fingerprints for any files that failed to scan this
    # run, so they aren't treated as newly-added on the next run.
    serialized: Dict[str, Dict] = {
        fp: serialize_file_fingerprints(fps)
        for fp, fps in current_fps.items()
    }
    for failed_path in failed_files:
        if failed_path in stored_raw:
            serialized[failed_path] = stored_raw[failed_path]

    baseline_stats = update_fingerprint_baseline(repo_path, serialized)
    print(
        "[docrot] Fingerprints updated: "
        f"files +{baseline_stats['files_added']} "
        f"-{baseline_stats['files_removed']} "
        f"~{baseline_stats['files_changed']} "
        f"={baseline_stats['files_unchanged']} | "
        f"functions +{baseline_stats['functions_added']} "
        f"-{baseline_stats['functions_removed']} "
        f"~{baseline_stats['functions_changed']} "
        f"={baseline_stats['functions_unchanged']}"
    )

    return 1 if (doc_alerts or flags) else 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Documentation Rot Detector")
    parser.add_argument(
        "repo_path",
        nargs="?",
        default=".",
        help="Path to the repository root (default: current directory)",
    )
    parser.add_argument(
        "--commit",
        default=None,
        help="Optional commit hash to embed in the report",
    )
    args = parser.parse_args()
    sys.exit(run(args.repo_path, commit_hash=args.commit))