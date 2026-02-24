"""
Alerts — Evaluate doc flags and publish results.

Converts scored ChangeEvents into DocAlerts that tell users
which documentation files may be stale and why.

MVP output: CI log warnings + a .docrot-report.json artifact.
Post-MVP: PR comments via GitHub API.
"""

import json
import os
from dataclasses import asdict
from typing import Any, Dict, List

from src.config import docs_for_code_path
from src.models import ChangeEvent, DocAlert


# ---------------------------------------------------------------------------
# Alert evaluation
# ---------------------------------------------------------------------------

def evaluate_doc_flags(function_events: List[ChangeEvent],
                       doc_mappings: List[Dict],
                       thresholds: Dict[str, int]) -> List[DocAlert]:
    """
    Decide which documentation files should be flagged for review.

    Flagging rules (MVP):
      - Per function: substantial if score >= per_function_substantial OR critical
      - Per doc file: flag if any critical event, OR cumulative score >= per_doc_cumulative

    Args:
        function_events: List of ChangeEvent objects from the comparator.
        doc_mappings:    Code→doc mapping list from config.
        thresholds:      Dict with per_function_substantial and per_doc_cumulative.

    Returns:
        List of DocAlert objects for docs that should be reviewed.
    """
    per_function_threshold = thresholds.get("per_function_substantial", 4)
    per_doc_threshold = thresholds.get("per_doc_cumulative", 8)

    # Accumulate scores per documentation file
    alerts_by_doc: Dict[str, Dict[str, Any]] = {}

    for event in function_events:
        # Find which docs are mapped to this code path
        mapped_docs = docs_for_code_path(event.code_path, doc_mappings)

        is_substantial = (event.score >= per_function_threshold) or event.critical

        for doc in mapped_docs:
            if doc not in alerts_by_doc:
                alerts_by_doc[doc] = {
                    "cumulative_score": 0,
                    "critical_found": False,
                    "reasons": [],
                    "functions": [],
                }

            info = alerts_by_doc[doc]
            info["cumulative_score"] += event.score
            info["critical_found"] = info["critical_found"] or event.critical
            info["reasons"].extend(event.reasons)
            if is_substantial:
                info["functions"].append(event.function_id)

    # Apply per-doc thresholds and build final alerts
    final_alerts: List[DocAlert] = []
    for doc_path, info in sorted(alerts_by_doc.items()):
        should_flag = info["critical_found"] or (info["cumulative_score"] >= per_doc_threshold)
        if should_flag:
            # De-duplicate reasons and functions
            unique_reasons = list(dict.fromkeys(info["reasons"]))
            unique_functions = list(dict.fromkeys(info["functions"]))

            final_alerts.append(DocAlert(
                doc_path=doc_path,
                message="Code logic changed; review this documentation for potential rot.",
                cumulative_score=info["cumulative_score"],
                critical_found=info["critical_found"],
                reasons=unique_reasons,
                functions=unique_functions,
            ))

    return final_alerts


# ---------------------------------------------------------------------------
# Alert publishing
# ---------------------------------------------------------------------------

def publish_alerts_to_log(alerts: List[DocAlert]) -> None:
    """
    Print human-readable warnings to stdout (CI log output).

    Args:
        alerts: List of DocAlert objects.
    """
    if not alerts:
        print("[docrot] No documentation files flagged for review.")
        return

    print(f"[docrot] {len(alerts)} documentation file(s) flagged for review:\n")
    for alert in alerts:
        critical_tag = " [CRITICAL]" if alert.critical_found else ""
        print(f"  WARNING{critical_tag}: {alert.doc_path}")
        print(f"    Cumulative score: {alert.cumulative_score}")
        print(f"    Reasons: {', '.join(alert.reasons)}")
        if alert.functions:
            print(f"    Affected functions: {', '.join(alert.functions)}")
        print()


REPORT_FILENAME = ".docrot-report.json"


def publish_alerts_to_report(alerts: List[DocAlert], repo_path: str) -> str:
    """
    Write alerts to a .docrot-report.json file as a CI artifact.

    Args:
        alerts:    List of DocAlert objects.
        repo_path: Root path of the repository.

    Returns:
        Path to the written report file.
    """
    report_path = os.path.join(repo_path, REPORT_FILENAME)
    report_data = {
        "docrot_report": {
            "alert_count": len(alerts),
            "alerts": [asdict(alert) for alert in alerts],
        }
    }
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, sort_keys=True)
        print(f"[docrot] Report written to {report_path}")
    except OSError as e:
        print(f"[docrot] Error: could not write report: {e}")
    return report_path


def publish_baseline_notice() -> None:
    """
    Called on the first run when no prior fingerprints exist.
    Informs the user that a baseline was generated and no alerts are emitted.
    """
    print("[docrot] First run detected. Baseline fingerprints generated. No alerts emitted.")
