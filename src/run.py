"""
run.py — Documentation Rot Detector entry point.

Usage:
    python run.py [repo_path]

If repo_path is omitted, the current working directory is used.

Pipeline:
    1. Load config (.docrot-config.json)
    2. Scan all Python source files → extract FunctionFingerprints
    3. On first run → save baseline, exit with no alerts
    4. On subsequent runs → compare against stored baseline
    5. Score semantic deltas → produce ChangeEvents
    6. Map changed functions to doc files → produce DocAlerts
    7. Print human-readable report + write .docrot-report.json
    8. Update stored fingerprints to the current snapshot
"""

import os
import sys
import time
from typing import Dict, Any

from src.ast_parser import extract_function_fingerprints
from src.comparator import compare_file_functions
from src.alerts import evaluate_doc_flags, publish_alerts_to_log, publish_alerts_to_report, publish_baseline_notice
from src.config import load_config, get_doc_mappings, get_thresholds
from src.models import FunctionFingerprint, ChangeEvent
from src.persistence import (
    is_first_run,
    load_fingerprints,
    persist_fingerprints,
    serialize_file_fingerprints,
    deserialize_file_fingerprints,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _collect_python_files(repo_path: str) -> list[str]:
    """
    Walk the repository and return all .py file paths (relative to repo_path).
    Skips hidden directories and common non-source folders.
    """
    SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", ".tox", "dist", "build"}
    py_files: list[str] = []

    for root, dirs, files in os.walk(repo_path):
        # Prune directories in-place so os.walk won't descend into them
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]

        for filename in files:
            if filename.endswith(".py"):
                abs_path = os.path.join(root, filename)
                rel_path = os.path.relpath(abs_path, repo_path).replace("\\", "/")
                py_files.append(rel_path)

    return sorted(py_files)


def _read_source(repo_path: str, rel_path: str) -> str | None:
    """Read a source file and return its contents, or None on error."""
    abs_path = os.path.join(repo_path, rel_path)
    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError as e:
        print(f"[docrot] Warning: could not read {rel_path}: {e}")
        return None


def _scan_repo(repo_path: str, py_files: list[str]) -> Dict[str, Dict[str, FunctionFingerprint]]:
    """
    Extract fingerprints for every function in every Python file.

    Returns:
        {rel_file_path: {stable_id: FunctionFingerprint}}
    """
    all_fingerprints: Dict[str, Dict[str, FunctionFingerprint]] = {}
    for rel_path in py_files:
        source = _read_source(repo_path, rel_path)
        if source is None:
            continue
        file_fps = extract_function_fingerprints(source, rel_path)
        if file_fps:
            all_fingerprints[rel_path] = file_fps
    return all_fingerprints


# ---------------------------------------------------------------------------
# Report printer
# ---------------------------------------------------------------------------

def _print_summary_report(
    change_events: list[ChangeEvent],
    alerts,
    elapsed: float,
    file_count: int,
    func_count: int,
) -> None:
    """Print the full mismatch report to stdout."""
    divider = "─" * 60

    print()
    print(divider)
    print("  Documentation Rot Detector — Scan Report")
    print(divider)
    print(f"  Files scanned  : {file_count}")
    print(f"  Functions found: {func_count}")
    print(f"  Scan time      : {elapsed:.2f}s")
    print(divider)

    if not change_events:
        print("  ✔  No code changes detected since last scan.")
        print(divider)
        print()
        return

    # ── Changed functions breakdown ──────────────────────────────────────
    print(f"\n  CODE CHANGES DETECTED ({len(change_events)} function(s))\n")

    critical_events = [e for e in change_events if e.critical]
    if critical_events:
        print(f"  ⚠  CRITICAL changes ({len(critical_events)}):")
        for event in critical_events:
            print(f"     • [{event.event_type}] {event.function_id}")
            print(f"       Reasons : {', '.join(event.reasons)}")
            print(f"       Score   : {event.score}")
        print()

    non_critical = [e for e in change_events if not e.critical]
    if non_critical:
        print(f"  ℹ  Non-critical changes ({len(non_critical)}):")
        for event in non_critical:
            print(f"     • [{event.event_type}] {event.function_id}")
            print(f"       Reasons : {', '.join(event.reasons)}")
            print(f"       Score   : {event.score}")
        print()

    print(divider)

    # ── Documentation alerts ─────────────────────────────────────────────
    if not alerts:
        print("  ✔  No documentation files flagged (scores below threshold).")
    else:
        print(f"\n  DOCUMENTATION FILES FLAGGED FOR REVIEW ({len(alerts)})\n")
        for alert in alerts:
            severity = "⚠  CRITICAL" if alert.critical_found else "ℹ  WARNING"
            print(f"  {severity}: {alert.doc_path}")
            print(f"     Cumulative score : {alert.cumulative_score}")
            print(f"     Reasons          : {', '.join(alert.reasons)}")
            if alert.functions:
                print(f"     Affected funcs   : {', '.join(alert.functions)}")
            print()

    print(divider)
    print()


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run(repo_path: str) -> int:
    """
    Execute the full detection pipeline for the given repository.

    Returns:
        Exit code: 0 = no issues, 1 = alerts found, 2 = error.
    """
    start_time = time.time()
    repo_path = os.path.abspath(repo_path)

    if not os.path.isdir(repo_path):
        print(f"[docrot] Error: '{repo_path}' is not a valid directory.")
        return 2

    print(f"[docrot] Scanning repository: {repo_path}")

    # 1. Load configuration
    config = load_config(repo_path)
    doc_mappings = get_doc_mappings(config)
    thresholds = get_thresholds(config)

    if not doc_mappings:
        print(
            "[docrot] Warning: no doc_mappings found in .docrot-config.json. "
            "Documentation alerts will not be generated.\n"
            "         Add a 'doc_mappings' section to .docrot-config.json to map "
            "source files to documentation files."
        )

    # 2. Collect Python source files
    py_files = _collect_python_files(repo_path)
    if not py_files:
        print("[docrot] No Python files found. Exiting.")
        return 0

    print(f"[docrot] Found {len(py_files)} Python file(s). Extracting fingerprints...")

    # 3. Extract current fingerprints
    current_fps = _scan_repo(repo_path, py_files)
    total_funcs = sum(len(fps) for fps in current_fps.values())
    print(f"[docrot] Extracted {total_funcs} function fingerprint(s).")

    # 4. First-run check → save baseline and exit
    if is_first_run(repo_path):
        serialized = {
            file_path: serialize_file_fingerprints(fps)
            for file_path, fps in current_fps.items()
        }
        persist_fingerprints(repo_path, serialized)
        publish_baseline_notice()
        elapsed = time.time() - start_time
        print(f"[docrot] Done in {elapsed:.2f}s.")
        return 0

    # 5. Load previous baseline
    stored_raw = load_fingerprints(repo_path)
    old_fps: Dict[str, Dict[str, FunctionFingerprint]] = {
        file_path: deserialize_file_fingerprints(fp_dict)
        for file_path, fp_dict in stored_raw.items()
    }

    # 6. Compare old vs new — collect ChangeEvents across all files
    all_events: list[ChangeEvent] = []
    all_file_paths = set(old_fps.keys()) | set(current_fps.keys())

    for file_path in sorted(all_file_paths):
        old_file_fps = old_fps.get(file_path, {})
        new_file_fps = current_fps.get(file_path, {})
        events = compare_file_functions(old_file_fps, new_file_fps, file_path)
        all_events.extend(events)

    # 7. Evaluate documentation alerts
    alerts = evaluate_doc_flags(all_events, doc_mappings, thresholds)

    # 8. Print the report
    elapsed = time.time() - start_time
    _print_summary_report(all_events, alerts, elapsed, len(py_files), total_funcs)

    # 9. Also write the JSON report artifact
    if all_events or alerts:
        publish_alerts_to_report(alerts, repo_path)

    # 10. Persist updated fingerprints as the new baseline
    serialized = {
        file_path: serialize_file_fingerprints(fps)
        for file_path, fps in current_fps.items()
    }
    persist_fingerprints(repo_path, serialized)
    print("[docrot] Fingerprints updated.")

    return 1 if alerts else 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "."
    sys.exit(run(path))
