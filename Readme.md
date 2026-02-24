
# Docrot Detector

## Overview

Docrot Detector is a tool that detects when Python code changes in semantically meaningful ways and flags linked documentation for review. It prevents documentation rot by analyzing code changes at the AST (Abstract Syntax Tree) level, scoring them with a weighted semantic model, and alerting when mapped documentation files may be stale.

Built as part of the CS 4485 Capstone course.

## How It Works

Docrot Detector runs as a pipeline with four stages:

1. **Change Detection** — Identify which `.py` files changed since the last run.
2. **AST Parsing & Fingerprinting** — Parse each file's AST, extract per-function semantic fingerprints (signature, control flow, conditions, calls, side effects, exceptions, returns).
3. **Comparison & Scoring** — Diff old vs. new fingerprints and apply a weighted scoring model to quantify how much each function's *behavior* changed.
4. **Alert Layer** — Map scored changes to documentation files via config and flag docs that exceed thresholds.

### Scoring Model

| Points | Change Type | Critical? |
|--------|-------------|-----------|
| 0 | Comment / formatting / docstring only | No |
| 1 | Literal/constant tweak, default argument tweak | No |
| 3 | Condition changed, loop changed, return changed | No |
| 5 | Public function signature changed, public API added/removed | **Yes** |
| 6 | Side-effect behavior changed (DB/file/network), auth/permission logic changed | **Yes** |
| 8 | Exception behavior changed, core control path added/removed | **Yes** |

A function is flagged as **substantial** if its score ≥ 4 or any critical event is present. A documentation file is flagged if any mapped function has a critical event, or the cumulative score across all mapped functions ≥ 8.

### First-Run Behavior

On the first run (no prior baseline), Docrot generates and stores fingerprints without emitting any alerts. Subsequent runs compare against the stored baseline.

## Features

- **Semantic AST Analysis** — Compares code structure and logic, not raw text diffs. Ignores formatting, comments, and docstring-only changes.
- **Weighted Scoring** — Tunable thresholds let teams adjust sensitivity for their needs.
- **Critical Event Triggers** — Public API changes, side-effect changes, auth logic changes, and exception behavior changes always flag regardless of score.
- **Doc Mapping** — JSON config maps code globs to documentation files.
- **CI-Friendly Output** — Prints warnings to stdout and writes a `.docrot-report.json` artifact.
- **Persistence** — Stores fingerprints in `.docrot-fingerprints.json` as the baseline for future comparisons.

## Folder Structure

```
.
├── API_Contract.md         # API design and contract documentation
├── Architecture.md         # System architecture and design notes
├── brainstorming.txt       # Project brainstorming and decisions
├── Proposal.md             # Project proposal document
├── pseudocode.py           # Pseudocode reference for the pipeline
├── Readme.md               # This file
├── database/
│   └── schema.sql          # Database schema (post-MVP: SQLite)
├── examples/
│   ├── example_basic_ast.py
│   ├── example_compare.py
│   ├── example_fingerprinting.py
│   ├── sample_code_v1.py   # Sample "before" code for testing
│   └── sample_code_v2.py   # Sample "after" code for testing
├── MeetingMinutes/
│   ├── CS4485_T2_MOM1.md
│   ├── CS4485_T2_MOM2.md
│   ├── README.md
│   └── WeeklyStatusReport.md
└── src/                    # Core source code
    ├── __init__.py
    ├── alerts.py           # Alert evaluation + CI/report publishing
    ├── ast_parser.py       # Python AST parsing + function extraction
    ├── comparator.py       # Feature diffing + weighted scoring engine
    ├── config.py           # Config loading + code→doc mapping
    ├── fingerprint.py      # Semantic feature extraction + hashing
    ├── models.py           # Dataclasses (fingerprints, deltas, events, alerts)
    └── persistence.py      # JSON fingerprint storage (load/save/serialize)
```

## Module Summary

| Module | Responsibility |
|--------|---------------|
| `models.py` | Dataclasses for `FunctionFingerprint`, `SemanticDelta`, `ChangeEvent`, `DocAlert`, plus serialization helpers |
| `config.py` | Loads `.docrot-config.json`, extracts doc mappings and thresholds, matches code paths to docs via fnmatch |
| `ast_parser.py` | Parses Python source → AST, finds all function/method nodes, builds stable IDs, orchestrates fingerprint extraction |
| `fingerprint.py` | 7 feature extractors (signature, control flow, conditions, calls, side effects, exceptions, returns), normalization, deterministic hashing, `build_fingerprint()` orchestrator |
| `comparator.py` | `diff_features()` compares fingerprints feature-by-feature; `score_semantic_delta()` applies weighted scoring; `compare_file_functions()` handles added/removed/modified functions |
| `persistence.py` | JSON-based fingerprint storage with `load_fingerprints()`, `persist_fingerprints()`, `is_first_run()`, and round-trip serialization |
| `alerts.py` | `evaluate_doc_flags()` accumulates per-doc scores and applies thresholds; `publish_alerts_to_log()` prints CI warnings; `publish_alerts_to_report()` writes `.docrot-report.json` |

## Configuration

Create a `.docrot-config.json` in the repository root:

```json
{
  "language": "python",
  "doc_mappings": [
    {
      "code_glob": "src/auth/*.py",
      "docs": ["docs/auth.md", "README.md"]
    },
    {
      "code_glob": "src/api/*.py",
      "docs": ["docs/api.md"]
    }
  ],
  "thresholds": {
    "per_function_substantial": 4,
    "per_doc_cumulative": 8
  }
}
```

- **`code_glob`** — fnmatch pattern matching source file paths.
- **`docs`** — List of documentation files that should be reviewed when matched code changes.
- **`per_function_substantial`** — Minimum score (or critical event) for a single function to count as a substantial change (default: 4).
- **`per_doc_cumulative`** — Minimum cumulative score across all functions for a doc file to be flagged (default: 8).

If the config file is missing, defaults are used (no doc mappings, standard thresholds).

## Setup

1. **Clone the repository:**
   ```sh
   git clone <repo-url>
   cd Docrot-Detector
   ```

2. **Python version:** Requires Python 3.8+. No external dependencies for MVP (uses only the standard library).

3. **(Optional) Create a virtual environment:**
   ```sh
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

## Quick Start

```python
from src.ast_parser import extract_function_fingerprints
from src.comparator import compare_file_functions
from src.alerts import evaluate_doc_flags, publish_alerts_to_log

# Extract fingerprints from old and new versions of a file
old_fps = extract_function_fingerprints(old_source_code, "src/auth/handlers.py")
new_fps = extract_function_fingerprints(new_source_code, "src/auth/handlers.py")

# Compare and get scored change events
events = compare_file_functions(old_fps, new_fps, "src/auth/handlers.py")

# Evaluate which docs should be flagged
doc_mappings = [{"code_glob": "src/auth/*.py", "docs": ["docs/auth.md"]}]
thresholds = {"per_function_substantial": 4, "per_doc_cumulative": 8}
alerts = evaluate_doc_flags(events, doc_mappings, thresholds)

# Output
publish_alerts_to_log(alerts)
```

## MVP Scope

- **Language:** Python only (uses the built-in `ast` module).
- **Trigger:** CI run or manual invocation.
- **Storage:** JSON file (`.docrot-fingerprints.json`). SQLite planned for post-MVP.
- **Output:** CI log warnings + `.docrot-report.json` artifact. PR comments planned for post-MVP.
- **Thresholds:** Global only. Per-module overrides planned for post-MVP.

## License

This project is for academic use as part of the CS 4485 Capstone course.
