"""
Docrot Detector — CLI entry point for quick testing.

Usage:
  python run.py <old_file> <new_file>              Compare two files, save results
  python run.py <file>                              Fingerprint a single file, save baseline
  python run.py examples/sample_code_v1.py examples/sample_code_v2.py

Output files (saved to repo root):
  .docrot-fingerprints.json   — Stored baseline fingerprints
  .docrot-report.json         — Alert report (compare mode only)
"""

import sys
import os

from src.ast_parser import extract_function_fingerprints
from src.comparator import compare_file_functions
from src.config import load_config, get_doc_mappings, get_thresholds
from src.alerts import evaluate_doc_flags, publish_alerts_to_log, publish_alerts_to_report, publish_baseline_notice
from src.persistence import (
    load_fingerprints, persist_fingerprints, is_first_run,
    serialize_file_fingerprints, deserialize_file_fingerprints,
)

# Repo root is wherever run.py lives
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))


def fingerprint_file(path):
    """Parse a single file, print fingerprints, and save to baseline."""
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()

    fps = extract_function_fingerprints(source, path)

    if not fps:
        print(f"No functions found in {path}")
        return

    print(f"Found {len(fps)} function(s) in {path}:\n")
    for sid, fp in fps.items():
        print(f"  {sid}")
        print(f"    public:      {fp.is_public}")
        print(f"    params:      {fp.signature.params}")
        print(f"    if/for/while: {fp.control_flow.if_count}/{fp.control_flow.for_count}/{fp.control_flow.while_count}")
        print(f"    calls:       {fp.calls.call_names}")
        print(f"    side effects: db={fp.side_effects.db_calls} file={fp.side_effects.file_calls} net={fp.side_effects.network_calls} auth={fp.side_effects.auth_calls}")
        print(f"    exceptions:  raises={fp.exceptions.raises} handlers={fp.exceptions.except_handlers}")
        print(f"    returns:     count={fp.returns.return_count} none={fp.returns.returns_none}")
        print(f"    hash:        {fp.fingerprint_hash[:16]}...")
        print()

    # Save to baseline
    stored = load_fingerprints(REPO_ROOT)
    stored[path] = serialize_file_fingerprints(fps)
    persist_fingerprints(REPO_ROOT, stored)
    print(f"Fingerprints saved to .docrot-fingerprints.json")


def compare_files(old_path, new_path):
    """Compare two files, print change events, save new baseline and report."""
    with open(old_path, "r", encoding="utf-8") as f:
        old_source = f.read()
    with open(new_path, "r", encoding="utf-8") as f:
        new_source = f.read()

    # Use the old path as the canonical code path
    code_path = old_path

    old_fps = extract_function_fingerprints(old_source, code_path)
    new_fps = extract_function_fingerprints(new_source, code_path)

    events = compare_file_functions(old_fps, new_fps, code_path)

    if not events:
        print("No semantic changes detected.")
    else:
        print(f"{len(events)} change(s) detected:\n")
        for e in events:
            tag = " [CRITICAL]" if e.critical else ""
            print(f"  {e.function_id}{tag}")
            print(f"    type:    {e.event_type}")
            print(f"    score:   {e.score}")
            print(f"    reasons: {', '.join(e.reasons)}")
            print()

    # Save new fingerprints as the updated baseline
    stored = load_fingerprints(REPO_ROOT)
    stored[code_path] = serialize_file_fingerprints(new_fps)
    persist_fingerprints(REPO_ROOT, stored)
    print(f"Updated baseline saved to .docrot-fingerprints.json")

    # Evaluate doc alerts using config (if available)
    if events:
        config = load_config(REPO_ROOT)
        doc_mappings = get_doc_mappings(config)
        thresholds = get_thresholds(config)
        alerts = evaluate_doc_flags(events, doc_mappings, thresholds)

        if alerts:
            print()
            publish_alerts_to_log(alerts)
            report_path = publish_alerts_to_report(alerts, REPO_ROOT)
        else:
            print("No documentation files flagged (no matching doc mappings or below threshold).")


def main():
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        print(__doc__.strip())
        sys.exit(0)

    if len(args) == 1:
        fingerprint_file(args[0])
    elif len(args) == 2:
        compare_files(args[0], args[1])
    else:
        print("Usage: python run.py <file> OR python run.py <old> <new>")
        sys.exit(1)


if __name__ == "__main__":
    main()
