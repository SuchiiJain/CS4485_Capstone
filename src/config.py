"""
Config — Load and validate the Docrot Detector configuration.

This module reads `.docrot-config.json` from the repository root and exposes
helpers used by the scan pipeline:

1) `doc_mappings`:
     - Maps changed source files to documentation files.
     - Matching is fnmatch/glob-style against repo-relative source paths.

2) `thresholds`:
     - `per_function_substantial`: minimum function score considered substantial.
     - `per_doc_cumulative`: minimum cumulative score required to flag a doc file.

Expected config shape:
{
    "language": "python",
    "doc_mappings": [
        {
            "code_glob": "src/*.py",
            "docs": ["Readme.md", "Architecture.md"]
        }
    ],
    "thresholds": {
        "per_function_substantial": 4,
        "per_doc_cumulative": 8
    }
}

Threshold behavior:
- If a threshold is missing, defaults are used.
- If a threshold is invalid (non-integer, <= 0), defaults are used.
- Threshold values are always returned as positive integers.

Post-MVP: per-module threshold overrides.
"""

import fnmatch
import json
import os
from typing import Any, Dict, List


DEFAULT_CONFIG: Dict[str, Any] = {
    "language": "python",
    "doc_mappings": [],
    "thresholds": {
        "per_function_substantial": 4,
        "per_doc_cumulative": 8,
    },
}

DEFAULT_THRESHOLDS: Dict[str, int] = {
    "per_function_substantial": 4,
    "per_doc_cumulative": 8,
}

CONFIG_FILENAME = ".docrot-config.json"


def _parse_positive_threshold(value: Any, key: str, default: int) -> int:
    """
    Parse and validate a threshold value.

    Args:
        value:   Candidate threshold value from config.
        key:     Threshold key name (for warning messages).
        default: Default value to use on invalid input.

    Returns:
        A positive integer threshold.
    """
    if isinstance(value, bool):
        print(f"[docrot] Warning: invalid threshold '{key}'={value}; using default {default}.")
        return default

    try:
        parsed = int(value)
    except (TypeError, ValueError):
        print(f"[docrot] Warning: invalid threshold '{key}'={value}; using default {default}.")
        return default

    if parsed <= 0:
        print(f"[docrot] Warning: threshold '{key}' must be > 0; using default {default}.")
        return default

    return parsed


def _normalize_thresholds(thresholds: Dict[str, Any]) -> Dict[str, int]:
    """
    Normalize threshold values to validated positive integers.

    Args:
        thresholds: Raw thresholds dict from config.

    Returns:
        Dict with validated threshold keys.
    """
    return {
        "per_function_substantial": _parse_positive_threshold(
            thresholds.get("per_function_substantial"),
            "per_function_substantial",
            DEFAULT_THRESHOLDS["per_function_substantial"],
        ),
        "per_doc_cumulative": _parse_positive_threshold(
            thresholds.get("per_doc_cumulative"),
            "per_doc_cumulative",
            DEFAULT_THRESHOLDS["per_doc_cumulative"],
        ),
    }


def load_config(repo_path: str) -> Dict[str, Any]:
    """
    Load configuration from .docrot-config.json in the repo root.

    Falls back to DEFAULT_CONFIG if the file is missing.

    Args:
        repo_path: Root path of the repository.

    Returns:
        Configuration dict with keys: language, doc_mappings, thresholds.
    """
    config_path = os.path.join(repo_path, CONFIG_FILENAME)
    if not os.path.exists(config_path):
        return dict(DEFAULT_CONFIG)

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            user_config = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"[docrot] Warning: could not read config ({e}); using defaults.")
        return dict(DEFAULT_CONFIG)

    # Merge user config over defaults (shallow merge per top-level key)
    merged: Dict[str, Any] = dict(DEFAULT_CONFIG)
    merged["language"] = user_config.get("language", merged["language"])
    merged["doc_mappings"] = user_config.get("doc_mappings", merged["doc_mappings"])

    user_thresholds = user_config.get("thresholds", {})
    if not isinstance(user_thresholds, dict):
        print("[docrot] Warning: 'thresholds' must be an object; using defaults.")
        user_thresholds = {}
    merged["thresholds"] = _normalize_thresholds(user_thresholds)

    return merged


def get_doc_mappings(config: Dict[str, Any]) -> List[Dict]:
    """
    Extract the doc_mappings list from config.

    Each mapping has:
      - code_glob: str   e.g. "src/auth/**/*.py"
      - docs: List[str]  e.g. ["docs/auth.md", "README.md"]

    Args:
        config: The loaded config dict.

    Returns:
        List of mapping dicts.
    """
    return config.get("doc_mappings", [])


def get_thresholds(config: Dict[str, Any]) -> Dict[str, int]:
    """
    Extract and validate threshold values from config.

    Keys:
      - per_function_substantial (default 4)
      - per_doc_cumulative (default 8)

    Args:
        config: The loaded config dict.

    Returns:
        Thresholds dict.
    """
    thresholds = config.get("thresholds", DEFAULT_THRESHOLDS)
    if not isinstance(thresholds, dict):
        return dict(DEFAULT_THRESHOLDS)
    return _normalize_thresholds(thresholds)


def get_threshold_info(config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Return current threshold values with defaults and descriptions.

    Useful for reporting, diagnostics, and printing config summaries.

    Args:
        config: The loaded config dict.

    Returns:
        Dict keyed by threshold name with metadata.
    """
    current = get_thresholds(config)
    return {
        "per_function_substantial": {
            "value": current["per_function_substantial"],
            "default": DEFAULT_THRESHOLDS["per_function_substantial"],
            "description": (
                "Minimum function change score considered substantial. "
                "Functions meeting/exceeding this are included as affected functions."
            ),
        },
        "per_doc_cumulative": {
            "value": current["per_doc_cumulative"],
            "default": DEFAULT_THRESHOLDS["per_doc_cumulative"],
            "description": (
                "Minimum cumulative score across mapped functions required "
                "to flag a documentation file."
            ),
        },
    }


def docs_for_code_path(code_path: str, doc_mappings: List[Dict]) -> List[str]:
    """
    Given a source file path, return all documentation files mapped to it.

    Uses fnmatch/glob-style matching on the code_glob patterns.

    Args:
        code_path:    Relative path to the changed source file.
        doc_mappings: List of mapping dicts from config.

    Returns:
        De-duplicated list of doc file paths that should be flagged.
    """
    matched_docs: List[str] = []
    # Normalize path separators to forward slashes for consistent matching
    normalized_path = code_path.replace("\\", "/")

    for mapping in doc_mappings:
        pattern = mapping.get("code_glob", "")
        docs = mapping.get("docs", [])
        # fnmatch works on individual path components; for glob-like ** patterns
        # we use fnmatch with the full path
        if fnmatch.fnmatch(normalized_path, pattern):
            matched_docs.extend(docs)

    # De-duplicate while preserving order
    seen: set = set()
    unique_docs: List[str] = []
    for doc in matched_docs:
        if doc not in seen:
            seen.add(doc)
            unique_docs.append(doc)

    return unique_docs
