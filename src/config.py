"""
Config — Load and validate the Docrot Detector configuration.

MVP config is a JSON file (.docrot-config.json) that maps source
code paths/globs to documentation files, plus global thresholds.

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

CONFIG_FILENAME = ".docrot-config.json"


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
    merged["thresholds"] = {
        "per_function_substantial": user_thresholds.get(
            "per_function_substantial",
            DEFAULT_CONFIG["thresholds"]["per_function_substantial"],
        ),
        "per_doc_cumulative": user_thresholds.get(
            "per_doc_cumulative",
            DEFAULT_CONFIG["thresholds"]["per_doc_cumulative"],
        ),
    }

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
    Extract threshold values from config.

    Keys:
      - per_function_substantial (default 4)
      - per_doc_cumulative (default 8)

    Args:
        config: The loaded config dict.

    Returns:
        Thresholds dict.
    """
    return config.get("thresholds", DEFAULT_CONFIG["thresholds"])


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
