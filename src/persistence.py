"""
Persistence — Load and save fingerprint snapshots.

MVP uses a JSON file (.docrot-fingerprints.json) as the single source
of truth for the "old" baseline. On each run we compare stored
fingerprints against freshly-extracted ones from the current code.

Post-MVP: migrate to SQLite for indexed queries and large-codebase support.
"""

import json
import os
from typing import Any, Dict

from src.models import FunctionFingerprint


FINGERPRINT_FILENAME = ".docrot-fingerprints.json"


def _fingerprint_path(repo_path: str) -> str:
    """Return the full path to the fingerprint JSON file."""
    return os.path.join(repo_path, FINGERPRINT_FILENAME)


def load_fingerprints(repo_path: str) -> Dict[str, Dict[str, Any]]:
    """
    Load previously stored fingerprints from the JSON file.

    Args:
        repo_path: Root path of the repository.

    Returns:
        Dict of {file_path: {stable_id: fingerprint_dict}}.
        Returns empty dict if the file does not exist (first run).
    """
    fp_path = _fingerprint_path(repo_path)
    if not os.path.exists(fp_path):
        return {}

    try:
        with open(fp_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"[docrot] Warning: could not read fingerprints ({e}); treating as first run.")
        return {}

    if not isinstance(data, dict):
        return {}

    return data


def persist_fingerprints(repo_path: str, fingerprints: Dict[str, Dict[str, Any]]) -> None:
    """
    Write current fingerprints to the JSON file, replacing the old baseline.

    The fingerprints dict structure is:
      {file_path: {stable_id: FunctionFingerprint.to_dict()}}

    Args:
        repo_path:    Root path of the repository.
        fingerprints: Dict of {file_path: {stable_id: fingerprint_dict}}.
    """
    fp_path = _fingerprint_path(repo_path)
    tmp_path = f"{fp_path}.tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(fingerprints, f, indent=2, sort_keys=True)
        os.replace(tmp_path, fp_path)
    except OSError as e:
        print(f"[docrot] Error: could not write fingerprints: {e}")
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass


def is_first_run(repo_path: str) -> bool:
    """
    Check whether prior fingerprints exist.

    First run → generate baseline only, emit zero alerts.

    Args:
        repo_path: Root path of the repository.

    Returns:
        True if no fingerprint file exists or it is empty.
    """
    fp_path = _fingerprint_path(repo_path)
    if not os.path.exists(fp_path):
        return True

    try:
        with open(fp_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return not bool(data)
    except (json.JSONDecodeError, OSError):
        return True


def serialize_file_fingerprints(
    fingerprints: Dict[str, FunctionFingerprint],
) -> Dict[str, Any]:
    """
    Convert a dict of {stable_id: FunctionFingerprint} to a JSON-serializable dict.

    Args:
        fingerprints: Dict mapping stable IDs to FunctionFingerprint objects.

    Returns:
        Dict mapping stable IDs to plain dicts.
    """
    return {sid: fp.to_dict() for sid, fp in fingerprints.items()}


def deserialize_file_fingerprints(
    data: Dict[str, Any],
) -> Dict[str, FunctionFingerprint]:
    """
    Convert a dict of {stable_id: plain_dict} back to FunctionFingerprint objects.

    Args:
        data: Dict mapping stable IDs to plain dicts (from JSON).

    Returns:
        Dict mapping stable IDs to FunctionFingerprint objects.
    """
    return {sid: FunctionFingerprint.from_dict(fp_dict) for sid, fp_dict in data.items()}


def update_fingerprint_baseline(
    repo_path: str,
    current_fingerprints: Dict[str, Dict[str, Any]],
) -> Dict[str, int]:
    """
    Update the fingerprint baseline and return a detailed change summary.

    This function compares the existing baseline with the current scan and
    reports what changed before persisting the new baseline.

    Args:
        repo_path: Root path of the repository.
        current_fingerprints: Current scan as
            {file_path: {stable_id: fingerprint_dict}}.

    Returns:
        Dict containing summary counters:
          - files_added
          - files_removed
          - files_changed
          - files_unchanged
          - functions_added
          - functions_removed
          - functions_changed
          - functions_unchanged
          - total_files
          - total_functions
    """
    old_fingerprints = load_fingerprints(repo_path)

    stats: Dict[str, int] = {
        "files_added": 0,
        "files_removed": 0,
        "files_changed": 0,
        "files_unchanged": 0,
        "functions_added": 0,
        "functions_removed": 0,
        "functions_changed": 0,
        "functions_unchanged": 0,
        "total_files": len(current_fingerprints),
        "total_functions": sum(len(v) for v in current_fingerprints.values()),
    }

    old_files = set(old_fingerprints.keys())
    new_files = set(current_fingerprints.keys())

    stats["files_added"] = len(new_files - old_files)
    stats["files_removed"] = len(old_files - new_files)

    for file_path in sorted(new_files):
        old_funcs = old_fingerprints.get(file_path, {})
        new_funcs = current_fingerprints.get(file_path, {})

        old_ids = set(old_funcs.keys())
        new_ids = set(new_funcs.keys())

        added_ids = new_ids - old_ids
        removed_ids = old_ids - new_ids
        common_ids = old_ids & new_ids

        stats["functions_added"] += len(added_ids)
        stats["functions_removed"] += len(removed_ids)

        changed_in_file = False
        if added_ids or removed_ids:
            changed_in_file = True

        for fn_id in common_ids:
            old_hash = old_funcs.get(fn_id, {}).get("fingerprint_hash", "")
            new_hash = new_funcs.get(fn_id, {}).get("fingerprint_hash", "")
            if old_hash == new_hash:
                stats["functions_unchanged"] += 1
            else:
                stats["functions_changed"] += 1
                changed_in_file = True

        if file_path in old_files:
            if changed_in_file:
                stats["files_changed"] += 1
            else:
                stats["files_unchanged"] += 1

    persist_fingerprints(repo_path, current_fingerprints)
    return stats
