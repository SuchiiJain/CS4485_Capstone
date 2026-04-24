import json
import os
from datetime import datetime
from typing import Optional

from src.flagging_threshold import Flag, Severity, FlagReason
from src.models import AISuggestion


# --- ScanReport Class ---

# Holds all the data for a single scan run, including repo info and all flags found
class ScanReport:
    def __init__(
        self,
        repo_path: str,
        commit_hash: Optional[str],
        flags: list[Flag],
        ai_suggestions: Optional[list[AISuggestion]] = None,
        ai_context: Optional[list[dict]] = None,
    ):
        self.repo_path = repo_path                    # Path to the scanned repository
        self.commit_hash = commit_hash or "unknown"   # Commit hash at time of scan
        self.timestamp = datetime.now().isoformat()   # Timestamp of when scan ran
        self.flags = flags                            # List of all flags found
        self.ai_suggestions = ai_suggestions or []    # Optional LLM-generated suggestions
        self.ai_context = ai_context or []            # Prompt context for backend AI processing

    # Returns a count of flags grouped by severity level
    def count_by_severity(self) -> dict[str, int]:
        counts = {"high": 0, "medium": 0, "low": 0}
        for f in self.flags:
            counts[f.severity.value] += 1
        return counts

    # Returns True if any flags were found during the scan
    def has_issues(self) -> bool:
        return len(self.flags) > 0


# --- Serialization Helper ---

# Converts a single Flag object into a dictionary for JSON output
def _flag_to_dict(flag: Flag) -> dict:
    data = {
        "reason": flag.reason.value,
        "severity": flag.severity.value,
        "code_element": {
            "name": flag.code_element.name,
            "file_path": flag.code_element.file_path,
            "signature": flag.code_element.signature,
            "params": flag.code_element.params,
            "return_type": flag.code_element.return_type,
        },
        # Only include doc_reference if one exists
        "doc_reference": {
            "file_path": flag.doc_reference.file_path,
            "referenced_symbol": flag.doc_reference.referenced_symbol,
            "snippet": flag.doc_reference.snippet,
        } if flag.doc_reference else None,
        "message": flag.message,
        "suggestion": flag.suggestion,
    }
    # Optional fields attached by _change_events_to_flags so the Cloud
    # Function can update the baseline entry after a successful auto-fix PR.
    new_fingerprint = getattr(flag, "new_fingerprint", None)
    if new_fingerprint is not None:
        data["new_fingerprint"] = new_fingerprint
    stable_id = getattr(flag, "stable_id", None)
    if stable_id is not None:
        data["stable_id"] = stable_id
    return data


# --- JSON Report Generator ---

# Generates a JSON report file from the scan results
# Defaults to .docrot-report.json at the repo root to match project convention
def generate_json_report(
    report: ScanReport, output_path: str = ".docrot-report.json"
) -> str:
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # Build the full report data structure
    data = {
        "meta": {
            "repo_path": report.repo_path,
            "commit_hash": report.commit_hash,
            "timestamp": report.timestamp,
            "total_issues": len(report.flags),
            "severity_summary": report.count_by_severity(),
        },
        "issues": [_flag_to_dict(f) for f in report.flags],
    }

    # Include AI suggestions if any were generated locally
    if report.ai_suggestions:
        data["ai_suggestions"] = [
            {
                "doc_path": s.doc_path,
                "triggered_by": s.triggered_by,
                "suggestion": s.suggestion_text,
                "model_used": s.model_used,
            }
            for s in report.ai_suggestions
        ]

    # Include AI context for backend processing
    if report.ai_context:
        data["ai_context"] = report.ai_context

    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    return output_path


# --- TXT Report Formatting ---

# Separator lines used for formatting the text report
_SEPARATOR = "=" * 60
_SUB_SEP = "-" * 60

# Display labels for each severity level in the text report
_SEVERITY_ICONS = {
    Severity.HIGH: "HIGH",
    Severity.MEDIUM: "MEDIUM",
    Severity.LOW: "LOW",
}


# Builds the header section of the text report
def _txt_header(report: ScanReport) -> list[str]:
    counts = report.count_by_severity()
    return [
        _SEPARATOR,
        " DOCUMENTATION ROT DETECTOR - SCAN REPORT",
        _SEPARATOR,
        f" Repo   : {report.repo_path}",
        f" Commit : {report.commit_hash}",
        f" Time   : {report.timestamp}",
        f" Issues : {len(report.flags)} total "
        f"(High: {counts['high']}, Medium: {counts['medium']}, Low: {counts['low']})",
        _SEPARATOR,
    ]


# Builds a single issue block for the text report
def _txt_flag_block(index: int, flag: Flag) -> list[str]:
    icon = _SEVERITY_ICONS.get(flag.severity, flag.severity.value)
    lines = [
        "",
        f" Issue #{index + 1} [{icon}]",
        _SUB_SEP,
        f" Reason    : {flag.reason.value}",
        f" Symbol    : {flag.code_element.name}",
        f" Code file : {flag.code_element.file_path}",
    ]
    # Only include signature if available
    if flag.code_element.signature:
        lines.append(f" Signature : {flag.code_element.signature}")
    # Only include doc info if a reference exists
    if flag.doc_reference:
        lines.append(f" Doc file  : {flag.doc_reference.file_path}")
        if flag.doc_reference.snippet:
            lines.append(f" Doc snippet: \"{flag.doc_reference.snippet[:80]}\"")
    lines.append("")
    lines.append(f" ! {flag.message}")
    # Only include suggestion if one was provided
    if flag.suggestion:
        lines.append(f" > Suggestion: {flag.suggestion}")
    return lines


# Builds the footer section of the text report
def _txt_footer(report: ScanReport) -> list[str]:
    return [
        "",
        _SEPARATOR,
        f" Scan complete. {len(report.flags)} issue(s) require attention.",
        _SEPARATOR,
        "",
    ]


# --- TXT Report Generator ---

# Generates a plain text report file from the scan results
# Defaults to .docrot-report.txt at the repo root to match project convention
def generate_txt_report(
    report: ScanReport, output_path: str = ".docrot-report.txt"
) -> str:
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    lines: list[str] = []
    lines.extend(_txt_header(report))

    if not report.has_issues():
        # No issues found — print a clean all-clear message
        lines.append("")
        lines.append(" No documentation rot detected. All docs are up to date!")
    else:
        # Add a block for each flag found
        for i, flag in enumerate(report.flags):
            lines.extend(_txt_flag_block(i, flag))

    # Append AI suggestions section if present
    if report.ai_suggestions:
        lines.append("")
        lines.append(_SEPARATOR)
        lines.append(" AI-GENERATED SUGGESTIONS")
        lines.append(_SEPARATOR)
        lines.append(f" Model: {report.ai_suggestions[0].model_used}")
        lines.append(" NOTE: These are AI-generated suggestions — review before applying.")
        for s in report.ai_suggestions:
            lines.append("")
            lines.append(_SUB_SEP)
            lines.append(f" Doc: {s.doc_path}")
            if s.triggered_by:
                lines.append(f" Triggered by: {', '.join(s.triggered_by)}")
            lines.append("")
            for line in s.suggestion_text.splitlines():
                lines.append(f"   {line}")

    lines.extend(_txt_footer(report))

    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return output_path


# --- Main Entry Point ---

# Generates both JSON and TXT reports from a list of flags
# This is the main function called by the rest of the system
def generate_reports(
    flags: list[Flag],
    repo_path: str,
    commit_hash: Optional[str] = None,
    json_path: str = ".docrot-report.json",
    txt_path: str = ".docrot-report.txt",
    ai_suggestions: Optional[list[AISuggestion]] = None,
    ai_context: Optional[list[dict]] = None,
) -> dict[str, str]:
    # Create the report object with all scan metadata
    report = ScanReport(
        repo_path=repo_path,
        commit_hash=commit_hash,
        flags=flags,
        ai_suggestions=ai_suggestions,
        ai_context=ai_context,
    )

    # Generate both output formats
    generate_txt_report(report, txt_path)
    generate_json_report(report, json_path)

    # Return paths to both generated files
    return {"txt": txt_path, "json": json_path} 