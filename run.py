"""
Docrot Detector — Automated manual test runner.

Usage:
    python run.py          Run all tests (single-file fingerprinting,
                           comparison, and full pipeline on test repos)

Tests performed:
    1. Single-file fingerprinting  (examples/sample_code_v1.py)
    2. Two-file comparison         (sample_code_v1.py vs sample_code_v2.py)
    3. Full pipeline — repo_basic  (baseline → swap v2 → detect changes)
    4. Full pipeline — repo_advanced (baseline → swap v2 → detect changes)
    5. Database storage            (save repo_basic report to SQLite)
"""

import sys
import os
import shutil
import json
import io

# Force UTF-8 output on Windows so the Unicode characters from src/run.py
# (box-drawing chars, warning signs, etc.) don't crash with cp1252.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True,
    )
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True,
    )

# Ensure project root is on sys.path so `src.*` imports work
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.ast_parser import extract_function_fingerprints
from src.comparator import compare_file_functions
from src.config import load_config, get_doc_mappings, get_thresholds
from src.alerts import (
    evaluate_doc_flags,
    publish_alerts_to_log,
    publish_alerts_to_report,
)
from src.persistence import (
    load_fingerprints,
    persist_fingerprints,
    serialize_file_fingerprints,
)
from src.run import run as run_pipeline
from backend.storage import init_db, save_scan, DB_PATH

# ── Paths ────────────────────────────────────────────────────────────────────
EXAMPLES_DIR = os.path.join(PROJECT_ROOT, "examples")
SAMPLE_V1 = os.path.join(EXAMPLES_DIR, "sample_code_v1.py")
SAMPLE_V2 = os.path.join(EXAMPLES_DIR, "sample_code_v2.py")

TEST_REPOS_DIR = os.path.join(EXAMPLES_DIR, "test_repos")
REPO_BASIC = os.path.join(TEST_REPOS_DIR, "repo_basic")
REPO_ADVANCED = os.path.join(TEST_REPOS_DIR, "repo_advanced")

SEP = "=" * 72
THIN_SEP = "-" * 72
PASS = "[PASS]"
FAIL = "[FAIL]"


def banner(title):
    """Print a section banner."""
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)


def sub_banner(title):
    """Print a sub-section banner."""
    print(f"\n{THIN_SEP}")
    print(f"  {title}")
    print(THIN_SEP)


# ── Cleanup helpers ──────────────────────────────────────────────────────────

# Generated artifacts to remove before/after repo pipeline tests
_REPO_ARTIFACTS = [
    ".docrot-fingerprints.json",
    ".docrot-report.json",
    ".docrot-report.txt",
]


def _clean_repo(repo_path):
    """Remove generated artifacts from a test repo."""
    for name in _REPO_ARTIFACTS:
        path = os.path.join(repo_path, name)
        if os.path.exists(path):
            os.remove(path)


def _restore_original_sources(repo_path, originals):
    """
    Restore original source files that were overwritten during v2 swap.
    `originals` is a dict of {dest_rel_path: original_content}.
    """
    for rel_path, content in originals.items():
        dest = os.path.join(repo_path, rel_path)
        with open(dest, "w", encoding="utf-8") as f:
            f.write(content)


# ── Test 1: Single-file fingerprinting ───────────────────────────────────────

def test_single_file_fingerprinting():
    banner("TEST 1: Single-File Fingerprinting")
    print(f"  File: {SAMPLE_V1}\n")

    with open(SAMPLE_V1, "r", encoding="utf-8") as f:
        source = f.read()

    fps = extract_function_fingerprints(source, "examples/sample_code_v1.py")

    if not fps:
        print(f"  {FAIL} No functions found!")
        return False

    print(f"  Found {len(fps)} function(s):\n")
    for sid, fp in fps.items():
        print(f"    {sid}")
        print(f"      public       : {fp.is_public}")
        print(f"      params       : {fp.signature.params}")
        print(f"      if/for/while : {fp.control_flow.if_count}/{fp.control_flow.for_count}/{fp.control_flow.while_count}")
        print(f"      calls        : {fp.calls.call_names}")
        print(f"      side effects : db={fp.side_effects.db_calls}  file={fp.side_effects.file_calls}  net={fp.side_effects.network_calls}  auth={fp.side_effects.auth_calls}")
        print(f"      exceptions   : raises={fp.exceptions.raises}  handlers={fp.exceptions.except_handlers}")
        print(f"      returns      : count={fp.returns.return_count}  none={fp.returns.returns_none}")
        print(f"      hash         : {fp.fingerprint_hash[:16]}...")
        print()

    # Verify expected functions exist
    expected = {"authenticate_user", "get_user_profile", "calculate_shipping", "_format_currency"}
    found = {fp.signature.name for fp in fps.values()}
    if expected == found:
        print(f"  {PASS} All 4 expected functions found with fingerprints.")
        return True
    else:
        missing = expected - found
        extra = found - expected
        print(f"  {FAIL} Function mismatch. Missing: {missing}, Extra: {extra}")
        return False


# ── Test 2: Two-file comparison ──────────────────────────────────────────────

def test_two_file_comparison():
    banner("TEST 2: Two-File Comparison (v1 vs v2)")
    print(f"  Old: {SAMPLE_V1}")
    print(f"  New: {SAMPLE_V2}\n")

    with open(SAMPLE_V1, "r", encoding="utf-8") as f:
        old_source = f.read()
    with open(SAMPLE_V2, "r", encoding="utf-8") as f:
        new_source = f.read()

    code_path = "examples/sample_code_v1.py"
    old_fps = extract_function_fingerprints(old_source, code_path)
    new_fps = extract_function_fingerprints(new_source, code_path)

    events = compare_file_functions(old_fps, new_fps, code_path)

    if not events:
        print(f"  {FAIL} No changes detected (expected several)!")
        return False

    print(f"  {len(events)} change(s) detected:\n")
    critical_count = 0
    for e in events:
        tag = " [CRITICAL]" if e.critical else ""
        print(f"    {e.function_id}{tag}")
        print(f"      type    : {e.event_type}")
        print(f"      score   : {e.score}")
        print(f"      reasons : {', '.join(e.reasons)}")
        print()
        if e.critical:
            critical_count += 1

    # Doc-alert evaluation using the project's root config
    config = load_config(PROJECT_ROOT)
    doc_mappings = get_doc_mappings(config)
    thresholds = get_thresholds(config)
    alerts = evaluate_doc_flags(events, doc_mappings, thresholds)

    if alerts:
        print("  Doc alerts generated:")
        for alert in alerts:
            crit = "CRITICAL" if alert.critical_found else "WARNING"
            print(f"    [{crit}] {alert.doc_path}  (score: {alert.cumulative_score})")
            print(f"      Reasons: {', '.join(alert.reasons)}")
        print()

    if len(events) >= 2 and critical_count >= 1:
        print(f"  {PASS} {len(events)} changes detected, {critical_count} critical.")
        return True
    else:
        print(f"  {FAIL} Expected at least 2 changes with 1+ critical.")
        return False


# ── Test 3 & 4: Full pipeline on test repos ─────────────────────────────────

def test_repo_pipeline(repo_path, repo_name, v2_swaps):
    """
    Run the full two-pass pipeline on a test repo.

    Args:
        repo_path:  Absolute path to the test repo.
        repo_name:  Display name (e.g. "repo_basic").
        v2_swaps:   List of (v2_source_rel, dest_rel) pairs, e.g.
                    [("src/auth_v2.py", "src/auth.py")].

    Returns:
        (passed: bool, report_json_path: str or None)
    """
    banner(f"TEST: Full Pipeline — {repo_name}")
    print(f"  Repo: {repo_path}\n")

    # Save original file contents so we can restore them after
    originals = {}
    for _, dest_rel in v2_swaps:
        dest = os.path.join(repo_path, dest_rel)
        with open(dest, "r", encoding="utf-8") as f:
            originals[dest_rel] = f.read()

    # Clean any leftover artifacts
    _clean_repo(repo_path)

    try:
        # ── Run 1: Create baseline ───────────────────────────────────────
        sub_banner(f"Run 1 — Baseline ({repo_name})")
        exit_code_1 = run_pipeline(repo_path)
        print(f"\n  Pipeline returned exit code: {exit_code_1}")

        baseline_file = os.path.join(repo_path, ".docrot-fingerprints.json")
        if not os.path.exists(baseline_file):
            print(f"  {FAIL} Baseline file was not created!")
            return False, None

        with open(baseline_file, "r", encoding="utf-8") as f:
            baseline_data = json.load(f)
        func_count = sum(len(v) for v in baseline_data.values())
        print(f"  Baseline created: {len(baseline_data)} file(s), {func_count} function(s)")
        print(f"  {PASS} Baseline created successfully.\n")

        # ── Swap in v2 files ─────────────────────────────────────────────
        sub_banner(f"Swapping in v2 files ({repo_name})")
        for v2_rel, dest_rel in v2_swaps:
            v2_path = os.path.join(repo_path, v2_rel)
            dest_path = os.path.join(repo_path, dest_rel)
            shutil.copy2(v2_path, dest_path)
            print(f"  Copied {v2_rel} -> {dest_rel}")
        print()

        # ── Run 2: Detect changes ───────────────────────────────────────
        sub_banner(f"Run 2 — Detect Changes ({repo_name})")
        exit_code_2 = run_pipeline(repo_path)
        print(f"\n  Pipeline returned exit code: {exit_code_2}")

        # Verify report files were generated
        report_json_path = os.path.join(repo_path, ".docrot-report.json")
        report_txt_path = os.path.join(repo_path, ".docrot-report.txt")

        has_json = os.path.exists(report_json_path)
        has_txt = os.path.exists(report_txt_path)

        print(f"\n  Report files:")
        print(f"    .docrot-report.json : {'EXISTS' if has_json else 'MISSING'}")
        print(f"    .docrot-report.txt  : {'EXISTS' if has_txt else 'MISSING'}")

        if has_json:
            with open(report_json_path, "r", encoding="utf-8") as f:
                report = json.load(f)
            meta = report.get("meta", {})
            sev = meta.get("severity_summary", {})
            issues = report.get("issues", [])
            print(f"\n  Report summary:")
            print(f"    Total issues : {meta.get('total_issues', '?')}")
            print(f"    High         : {sev.get('high', 0)}")
            print(f"    Medium       : {sev.get('medium', 0)}")
            print(f"    Low          : {sev.get('low', 0)}")
            print(f"    Issues list  : {len(issues)} item(s)")

        if has_txt:
            print(f"\n  Content of .docrot-report.txt:")
            print(THIN_SEP)
            with open(report_txt_path, "r", encoding="utf-8") as f:
                print(f.read())
            print(THIN_SEP)

        if exit_code_2 == 1 and has_json and has_txt:
            print(f"  {PASS} Changes detected and reports generated for {repo_name}.")
            return True, report_json_path
        else:
            print(f"  {FAIL} Expected exit code 1 with report files.")
            return False, report_json_path if has_json else None

    finally:
        # Always restore originals and clean up, even if test fails
        _restore_original_sources(repo_path, originals)
        _clean_repo(repo_path)


# ── Test 5: Database storage ────────────────────────────────────────────────

def test_database_storage(report_json_path, repo_name):
    """Save a report to the SQLite database and verify it was stored."""
    banner("TEST 5: Database Storage (SQLite)")

    if report_json_path is None or not os.path.exists(report_json_path):
        print(f"  {FAIL} No report JSON available to store.")
        return False

    with open(report_json_path, "r", encoding="utf-8") as f:
        report_json = json.load(f)

    # Remove old test database if it exists
    db_abs = os.path.join(PROJECT_ROOT, DB_PATH)
    if os.path.exists(db_abs):
        os.remove(db_abs)

    print(f"  Initializing database at: {db_abs}")
    init_db()

    print(f"  Saving scan for '{repo_name}'...")
    save_scan(repo_name, "test-commit-abc123", report_json)

    # Verify by reading back
    import sqlite3
    conn = sqlite3.connect(db_abs)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM scan_runs")
    scan_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM flags")
    flag_count = cur.fetchone()[0]

    cur.execute("SELECT id, repo_name, total_issues, high_count, medium_count, low_count FROM scan_runs")
    row = cur.fetchone()
    conn.close()

    print(f"\n  Database contents:")
    print(f"    scan_runs rows : {scan_count}")
    print(f"    flags rows     : {flag_count}")
    if row:
        print(f"    Scan ID        : {row[0][:12]}...")
        print(f"    Repo name      : {row[1]}")
        print(f"    Total issues   : {row[2]}")
        print(f"    High/Med/Low   : {row[3]}/{row[4]}/{row[5]}")

    if scan_count == 1 and flag_count > 0:
        print(f"\n  {PASS} Report successfully stored in database ({flag_count} flags).")
        return True
    else:
        print(f"\n  {FAIL} Expected 1 scan and >0 flags in database.")
        return False


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    results = {}

    # Test 1: Single-file fingerprinting
    results["Single-file fingerprinting"] = test_single_file_fingerprinting()

    # Test 2: Two-file comparison
    results["Two-file comparison"] = test_two_file_comparison()

    # Test 3: Full pipeline — repo_basic
    # We need to keep the report JSON around for the DB test, so we handle
    # cleanup slightly differently here: we run the test, grab the report
    # path before cleanup, and copy the report to a temp location.
    passed_basic, report_basic = _run_repo_test_with_report_copy(
        REPO_BASIC, "repo_basic",
        [("src/auth_v2.py", "src/auth.py"),
         ("src/utils_v2.py", "src/utils.py")],
    )
    results["Full pipeline (repo_basic)"] = passed_basic

    # Test 4: Full pipeline — repo_advanced
    passed_adv, report_adv = _run_repo_test_with_report_copy(
        REPO_ADVANCED, "repo_advanced",
        [("src/payments_v2.py", "src/payments.py"),
         ("src/database_v2.py", "src/database.py")],
    )
    results["Full pipeline (repo_advanced)"] = passed_adv

    # Test 5: Database storage (using repo_basic report)
    results["Database storage"] = test_database_storage(report_basic, "repo_basic")

    # Clean up temp report copies
    for tmp in (report_basic, report_adv):
        if tmp and os.path.exists(tmp):
            os.remove(tmp)

    # ── Summary ──────────────────────────────────────────────────────────
    banner("TEST SUMMARY")
    all_passed = True
    for name, passed in results.items():
        status = PASS if passed else FAIL
        print(f"  {status}  {name}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print(f"  All {len(results)} tests passed!")
    else:
        failed = sum(1 for p in results.values() if not p)
        print(f"  {failed}/{len(results)} test(s) failed.")
    print(f"{SEP}\n")

    return 0 if all_passed else 1


def _run_repo_test_with_report_copy(repo_path, repo_name, v2_swaps):
    """
    Run a repo pipeline test. Because the test cleans up artifacts at the end,
    we need to copy the report JSON to a temp file before cleanup so the DB
    test can use it.
    """
    # Save originals
    originals = {}
    for _, dest_rel in v2_swaps:
        dest = os.path.join(repo_path, dest_rel)
        with open(dest, "r", encoding="utf-8") as f:
            originals[dest_rel] = f.read()

    _clean_repo(repo_path)

    report_copy_path = None
    try:
        # Run 1: Baseline
        sub_banner(f"Run 1 — Baseline ({repo_name})")
        exit_code_1 = run_pipeline(repo_path)
        print(f"\n  Pipeline returned exit code: {exit_code_1}")

        baseline_file = os.path.join(repo_path, ".docrot-fingerprints.json")
        if not os.path.exists(baseline_file):
            print(f"  {FAIL} Baseline file was not created!")
            return False, None

        with open(baseline_file, "r", encoding="utf-8") as f:
            baseline_data = json.load(f)
        func_count = sum(len(v) for v in baseline_data.values())
        print(f"  Baseline created: {len(baseline_data)} file(s), {func_count} function(s)")
        print(f"  {PASS} Baseline created successfully.\n")

        # Swap in v2 files
        sub_banner(f"Swapping in v2 files ({repo_name})")
        for v2_rel, dest_rel in v2_swaps:
            v2_path = os.path.join(repo_path, v2_rel)
            dest_path = os.path.join(repo_path, dest_rel)
            shutil.copy2(v2_path, dest_path)
            print(f"  Copied {v2_rel} -> {dest_rel}")
        print()

        # Run 2: Detect changes
        sub_banner(f"Run 2 — Detect Changes ({repo_name})")
        exit_code_2 = run_pipeline(repo_path)
        print(f"\n  Pipeline returned exit code: {exit_code_2}")

        # Check report files
        report_json_path = os.path.join(repo_path, ".docrot-report.json")
        report_txt_path = os.path.join(repo_path, ".docrot-report.txt")

        has_json = os.path.exists(report_json_path)
        has_txt = os.path.exists(report_txt_path)

        print(f"\n  Report files:")
        print(f"    .docrot-report.json : {'EXISTS' if has_json else 'MISSING'}")
        print(f"    .docrot-report.txt  : {'EXISTS' if has_txt else 'MISSING'}")

        if has_json:
            with open(report_json_path, "r", encoding="utf-8") as f:
                report = json.load(f)
            meta = report.get("meta", {})
            sev = meta.get("severity_summary", {})
            issues = report.get("issues", [])
            print(f"\n  Report summary:")
            print(f"    Total issues : {meta.get('total_issues', '?')}")
            print(f"    High         : {sev.get('high', 0)}")
            print(f"    Medium       : {sev.get('medium', 0)}")
            print(f"    Low          : {sev.get('low', 0)}")
            print(f"    Issues list  : {len(issues)} item(s)")

            # Copy report for DB test before cleanup
            report_copy_path = os.path.join(PROJECT_ROOT, f".tmp-report-{repo_name}.json")
            shutil.copy2(report_json_path, report_copy_path)

        if has_txt:
            print(f"\n  Content of .docrot-report.txt:")
            print(THIN_SEP)
            with open(report_txt_path, "r", encoding="utf-8") as f:
                print(f.read())
            print(THIN_SEP)

        passed = exit_code_2 == 1 and has_json and has_txt
        if passed:
            print(f"  {PASS} Changes detected and reports generated for {repo_name}.")
        else:
            print(f"  {FAIL} Expected exit code 1 with report files (got exit code {exit_code_2}).")

        return passed, report_copy_path

    finally:
        _restore_original_sources(repo_path, originals)
        _clean_repo(repo_path)


if __name__ == "__main__":
    sys.exit(main())
