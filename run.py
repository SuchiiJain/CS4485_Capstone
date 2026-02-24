"""
Docrot Detector — CLI entry point for quick testing.

Usage:
  python run.py <old_file> <new_file>              Compare two files
  python run.py <file>                              Fingerprint a single file
  python run.py examples/sample_code_v1.py examples/sample_code_v2.py
"""

import sys
import os

from src.ast_parser import extract_function_fingerprints
from src.comparator import compare_file_functions
from src.alerts import evaluate_doc_flags, publish_alerts_to_log


def fingerprint_file(path):
    """Parse and print fingerprints for a single file."""
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


def compare_files(old_path, new_path):
    """Compare two files and print change events."""
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
        return

    print(f"{len(events)} change(s) detected:\n")
    for e in events:
        tag = " [CRITICAL]" if e.critical else ""
        print(f"  {e.function_id}{tag}")
        print(f"    type:    {e.event_type}")
        print(f"    score:   {e.score}")
        print(f"    reasons: {', '.join(e.reasons)}")
        print()


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
