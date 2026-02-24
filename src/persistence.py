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
    try:
        with open(fp_path, "w", encoding="utf-8") as f:
            json.dump(fingerprints, f, indent=2, sort_keys=True)
    except OSError as e:
        print(f"[docrot] Error: could not write fingerprints: {e}")


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
