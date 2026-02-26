import json
import os
from datetime import datetime
from typing import Optional

from flagging_threshold import Flag, Severity, FlagReason


class ScanReport:
    def __init__(self, repo_path: str, commit_hash: Optional[str], flags: list[Flag]):
        self.repo_path = repo_path
        self.commit_hash = commit_hash or "unknown"
        self.timestamp = datetime.now().isoformat()
        self.flags = flags

    def count_by_severity(self) -> dict[str, int]:
        counts = {"high": 0, "medium": 0, "low": 0}
        for f in self.flags:
            counts[f.severity.value] += 1
        return counts

    def has_issues(self) -> bool:
        return len(self.flags) > 0


def _flag_to_dict(flag: Flag) -> dict:
    return {
        "reason": flag.reason.value,
        "severity": flag.severity.value,
        "code_element": {
            "name": flag.code_element.name,
            "file_path": flag.code_element.file_path,
            "signature": flag.code_element.signature,
            "params": flag.code_element.params,
            "return_type": flag.code_element.return_type,
        },
        "doc_reference": {
            "file_path": flag.doc_reference.file_path,
            "referenced_symbol": flag.doc_reference.referenced_symbol,
            "snippet": flag.doc_reference.snippet,
        } if flag.doc_reference else None,
        "message": flag.message,
        "suggestion": flag.suggestion,
    }


def generate_json_report(
    report: ScanReport, output_path: str = ".docrot-report.json"
) -> str:
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
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
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    return output_path


_SEPARATOR = "=" * 60
_SUB_SEP = "-" * 60
_SEVERITY_ICONS = {
    Severity.HIGH: "HIGH",
    Severity.MEDIUM: "MEDIUM",
    Severity.LOW: "LOW",
}


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
    if flag.code_element.signature:
        lines.append(f" Signature : {flag.code_element.signature}")
    if flag.doc_reference:
        lines.append(f" Doc file  : {flag.doc_reference.file_path}")
        if flag.doc_reference.snippet:
            lines.append(f" Doc snippet: \"{flag.doc_reference.snippet[:80]}\"")
    lines.append("")
    lines.append(f" ! {flag.message}")
    if flag.suggestion:
        lines.append(f" > Suggestion: {flag.suggestion}")
    return lines


def _txt_footer(report: ScanReport) -> list[str]:
    return [
        "",
        _SEPARATOR,
        f" Scan complete. {len(report.flags)} issue(s) require attention.",
        _SEPARATOR,
        "",
    ]


def generate_txt_report(
    report: ScanReport, output_path: str = ".docrot-report.txt"
) -> str:
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    lines: list[str] = []
    lines.extend(_txt_header(report))
    if not report.has_issues():
        lines.append("")
        lines.append(" No documentation rot detected. All docs are up to date!")
    else:
        for i, flag in enumerate(report.flags):
            lines.extend(_txt_flag_block(i, flag))
    lines.extend(_txt_footer(report))
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return output_path


def generate_reports(
    flags: list[Flag],
    repo_path: str,
    commit_hash: Optional[str] = None,
    json_path: str = ".docrot-report.json",
    txt_path: str = ".docrot-report.txt",
) -> dict[str, str]:
    report = ScanReport(repo_path=repo_path, commit_hash=commit_hash, flags=flags)
    generate_txt_report(report, txt_path)
    generate_json_report(report, json_path)
    return {"txt": txt_path, "json": json_path}