
# Docrot Detector

## Overview

Docrot Detector is a tool that detects when Python code changes in semantically meaningful ways and flags linked documentation for review. It prevents documentation rot by analyzing code changes at the AST (Abstract Syntax Tree) level, scoring them with a weighted semantic model, and alerting when mapped documentation files may be stale.

Built as part of the CS 4485 Capstone course.

## How It Works

Docrot Detector runs as a pipeline with four stages:

1. **Repository Scan** — Discover all `.py` files in the target repo (excluding `.git`, `__pycache__`, `.venv`, etc.).
2. **AST Parsing & Fingerprinting** — Parse each file's AST, extract per-function semantic fingerprints (signature, control flow, conditions, calls, side effects, exceptions, returns).
3. **Comparison & Scoring** — Diff old vs. new fingerprints and apply a weighted scoring model to quantify how much each function's *behavior* changed.
4. **Alert Layer + Baseline Update** — Map scored changes to documentation files via config, flag docs that exceed thresholds, then persist the updated baseline.

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

On the first run (no prior baseline), Docrot generates and stores fingerprints without emitting any alerts.

On subsequent runs, Docrot compares current fingerprints against the stored baseline, reports semantic changes, and then updates the baseline with summary stats (files/functions added, removed, changed, unchanged).

## Features

- **Semantic AST Analysis** — Compares code structure and logic, not raw text diffs. Ignores formatting, comments, and docstring-only changes.
- **Weighted Scoring** — Tunable thresholds let teams adjust sensitivity for their needs.
- **Critical Event Triggers** — Public API changes, side-effect changes, auth logic changes, and exception behavior changes always flag regardless of score.
- **Doc Mapping** — JSON config maps code globs to documentation files.
- **CI-Friendly Output** — Prints warnings to stdout and writes a `.docrot-report.json` artifact.
- **Persistence** — Stores fingerprints in `.docrot-fingerprints.json` as the baseline for future comparisons, with detailed baseline update stats each run.
- **Safer Baseline Writes** — Fingerprint persistence uses a temp-file + replace flow to reduce risk of partial/corrupted baseline writes.

## Folder Structure

```
.
├── Readme.md               # This file
├── run.py                  # Quick-test CLI (compare two files or fingerprint one)
├── docs/
│   ├── API_Contract.md     # API design and contract documentation
│   ├── Architecture.md     # System architecture and design notes
│   ├── Proposal.md         # Project proposal document
│   ├── brainstorming.txt   # Project brainstorming and decisions
│   └── pseudocode.py       # Pseudocode reference for the pipeline
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
│   ├── CS4485_T2_MOM3.md
│   ├── CS4485_T2_MOM4.md
│   ├── CS4485_T2_MOM5.md
│   ├── CS4485_T2_MOM6.md 
│   ├── README.md
│   └── WeeklyStatusReport.md
└── src/                    # Core source code
    ├── __init__.py
    ├── alerts.py           # Alert evaluation + CI/report publishing
    ├── ast_parser.py       # Python AST parsing + function extraction
    ├── comparator.py       # Feature diffing + weighted scoring engine
    ├── config.py           # Config loading + code→doc mapping
    ├── fingerprint.py      # Semantic feature extraction + hashing
    ├── flagging_threshold.py  # Flag dataclasses, severity enums, and all check functions
    ├── models.py           # Dataclasses (fingerprints, deltas, events, alerts)
    ├── persistence.py      # JSON fingerprint storage (load/save/serialize)
    ├── flagging_threshold.py  # Flag dataclasses, severity enums, and all check functions
    ├── report_generation.py     # Generates .txt and .json scan reports from flags
    ├── run.py                # Full pipeline entry point (scan entire repo)
    ├── webhook_server.py     # Flask webhook server for GitHub push events
    └── github_integration.py # Git clone/pull + GitHub API (commit statuses)
    ├── report_generation.py   # Generates .txt and .json scan reports from flags
    └── run.py              # Full pipeline entry point (scan entire repo)
```

## Module Summary

| Module | Responsibility |
|--------|---------------|
| `models.py` | Dataclasses for `FunctionFingerprint`, `SemanticDelta`, `ChangeEvent`, `DocAlert`, plus serialization helpers |
| `config.py` | Loads `.docrot-config.json`, extracts doc mappings and thresholds, matches code paths to docs via fnmatch |
| `ast_parser.py` | Parses Python source → AST, finds all function/method nodes, builds stable IDs, orchestrates fingerprint extraction |
| `fingerprint.py` | 7 feature extractors (signature, control flow, conditions, calls, side effects, exceptions, returns), normalization, deterministic hashing, `build_fingerprint()` orchestrator |
| `comparator.py` | `diff_features()` compares fingerprints feature-by-feature; `score_semantic_delta()` applies weighted scoring; `compare_file_functions()` handles added/removed/modified functions |
| `persistence.py` | JSON-based fingerprint storage with `load_fingerprints()`, `persist_fingerprints()`, `update_fingerprint_baseline()`, `is_first_run()`, and round-trip serialization |
| `alerts.py` | `evaluate_doc_flags()` accumulates per-doc scores and applies thresholds; `publish_alerts_to_log()` prints CI warnings; `publish_alerts_to_report()` writes `.docrot-report.json` |
| `flagging_threshold.py` | Flag dataclasses (`Flag`, `CodeElement`, `DocReference`), severity enums, `SEVERITY_MAP`, and all `check_*` detection functions |
| `report_generation.py` | `ScanReport` class, `generate_txt_report()`, `generate_json_report()`, and `generate_reports()` entry point — outputs `.docrot-report.txt` and `.docrot-report.json` |
| `src/run.py` | Full pipeline entry point — scans an entire repo directory, extracts fingerprints for all `.py` files, compares against stored baseline, scores changes, maps to docs, prints a summary report, and writes JSON artifacts |
| `src/webhook_server.py` | Flask app that receives GitHub webhook `push` events, verifies HMAC signatures, and spawns background pipeline runs |
| `src/github_integration.py` | Clones/pulls repos via git CLI, posts commit statuses and PR comments via the GitHub REST API |

## Configuration

Create a `.docrot-config.json` in the repository root:

```json
{
  "language": "python",
  "doc_mappings": [
    {
      "code_glob": "src/*.py",
      "docs": ["Readme.md", "docs/Architecture.md"]
    },
    {
      "code_glob": "examples/*.py",
      "docs": ["examples/fakedoc.md"]
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
- **`per_function_substantial`** — Minimum score for a function change to be considered substantial (default: 4).
- **`per_doc_cumulative`** — Minimum cumulative score across mapped functions for a doc file to be flagged (default: 8).

### Threshold Validation & Defaults

Docrot now validates thresholds when loading config:

- Missing threshold values fall back to defaults.
- Invalid values (non-numeric, boolean, or `<= 0`) are rejected and replaced with defaults.
- Loaded thresholds are normalized to positive integers before use.
- If `thresholds` is not a JSON object, Docrot logs a warning and uses defaults.

Default thresholds:

```json
{
  "per_function_substantial": 4,
  "per_doc_cumulative": 8
}
```

Meaning in the pipeline:

- A function is treated as substantial when its score is `>= per_function_substantial` or it is critical.
- A documentation file is flagged when any mapped change is critical, or when cumulative mapped score is `>= per_doc_cumulative`.

### Mapping Notes

- `code_glob` is matched against repo-relative file paths (normalized to forward slashes).
- Multiple mappings may match the same source file; doc paths are de-duplicated.
- If no `doc_mappings` are provided, code changes are still analyzed, but doc-file alerts are not generated.

If the config file is missing, defaults are used (no doc mappings, standard thresholds).

## Setup

1. **Clone the repository:**
   ```sh
   git clone <repo-url>
   cd CS4485_Capstone
   ```

2. **Python version:** Requires Python 3.8+. No external dependencies for MVP (uses only the standard library).

3. **(Optional) Create a virtual environment:**
   ```sh
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

## Usage

All commands are run from the repo root directory.

### Full Repository Scan (Recommended)

The primary way to use Docrot Detector is `src/run.py`, which scans an entire repository:

```sh
# Scan the current directory
python -m src.run .

# Scan a specific repo path
python -m src.run /path/to/your/repo
```

This runs the full pipeline:
1. Finds all `.py` files in the repo (skipping `.git`, `__pycache__`, `venv`, etc.)
2. Extracts semantic fingerprints for every function/method
3. On **first run**: saves a baseline to `.docrot-fingerprints.json` and exits with no alerts
4. On **subsequent runs**: compares against the stored baseline, scores changes, flags documentation files for review, prints a formatted summary report, and updates the baseline
5. Prints a baseline-update summary showing file/function deltas (`+` added, `-` removed, `~` changed, `=` unchanged)

**Exit codes** (useful for CI):
| Code | Meaning |
|------|---------|
| 0 | No alerts (clean) or first-run baseline generated |
| 1 | Documentation alerts were raised |
| 2 | Error (e.g., invalid repo path) |

### Quick-Test CLI (Manual Comparison)

The root `run.py` is a simpler tool for ad-hoc testing of individual files:

```sh
# Compare two files (detect changes between versions)
python run.py examples/sample_code_v1.py examples/sample_code_v2.py

# Inspect a single file's fingerprints
python run.py examples/sample_code_v1.py

# Help
python run.py --help
```

### Output Files

Both entry points save results to the repo root:

| File | When created | Contents |
|------|-------------|----------|
| `.docrot-fingerprints.json` | Every run | Stored baseline fingerprints — updated after each run so the next comparison uses the latest state |
| `.docrot-report.txt` | When code changes are detected | Human-readable report with severity summary and flagged items |
| `.docrot-report.json` | When doc alerts are triggered | JSON report of flagged documentation files (requires a `.docrot-config.json` with doc mappings) |

### Programmatic Usage

You can also import the modules directly in Python:

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

## GitHub Action (Recommended)

The easiest way to use Docrot Detector is as a GitHub Action. No server, no tokens to configure — just add a workflow file to your repo.

### Quick Start

Create `.github/workflows/docrot.yml` in your repository:

```yaml
name: Docrot Detector
on: [push]

jobs:
  docrot:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      issues: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: SuchiiJain/CS4485_Capstone@main
```

That's it. On every push, Docrot will:
1. Scan all Python files for semantic code changes
2. Compare against the stored baseline (`.docrot-fingerprints.json`)
3. If documentation rot is detected, **create a GitHub issue** with a detailed report
4. If a previous issue exists and the scan is now clean, **close it automatically**

### Action Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `repo_path` | No | `.` | Path to the repository root to scan |
| `create_issue` | No | `true` | Create/update a GitHub issue when alerts are found |

### Configuration

The Action reads `.docrot-config.json` from the root of the repo it's scanning. This is how users configure doc mappings and thresholds — just add the file to their own repo:

```json
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
```

If the file is absent, Docrot runs with no doc mappings and default thresholds — it will still scan and report function-level changes, but won't flag specific documentation files.

### How It Works

- The Action uses the `GITHUB_TOKEN` provided automatically by GitHub Actions — no PATs or shared accounts needed.
- A `docrot` label is created automatically on the first alert.
- If alerts are found, a single issue is created (or the existing one is updated).
- When a subsequent scan is clean, the issue is closed automatically.

## GitHub Webhook Server

Docrot can also run as a webhook server that automatically scans repos when code is pushed to GitHub.

### Quick Start

```sh
# Install webhook dependencies
pip install -r requirements.txt

# Set your webhook secret
export DOCROT_WEBHOOK_SECRET=$(python -c "import secrets; print(secrets.token_hex(32))")

# (Optional) Set a GitHub token for private repos + commit status posting
export GITHUB_TOKEN=ghp_your_token_here

# Start the server
python -m src.webhook_server
```

### Setting Up the GitHub Webhook

1. Go to your GitHub repo → **Settings** → **Webhooks** → **Add webhook**
2. **Payload URL**: `http://<your-server>:5000/webhook`
3. **Content type**: `application/json`
4. **Secret**: paste the same value as `DOCROT_WEBHOOK_SECRET`
5. **Events**: select "Just the push event"
6. Click **Add webhook**

Now every push to the repo will trigger a Docrot scan. If `GITHUB_TOKEN` is set, results appear as commit status checks (✓/✗) on commits and PRs.

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/webhook` | POST | GitHub webhook receiver |
| `/health` | GET | Health check |

### Environment Variables

See `.env.example` for the full list. Key variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `DOCROT_WEBHOOK_SECRET` | Yes | Shared HMAC secret for signature verification |
| `GITHUB_TOKEN` | No | PAT for private repos + commit status posting |
| `DOCROT_CLONE_DIR` | No | Directory for cloned repos (default: `./repos`) |
| `DOCROT_PORT` | No | Server port (default: `5000`) |

## MVP Scope

- **Language:** Python only (uses the built-in `ast` module).
- **Trigger:** GitHub webhook (push events), CI run, or manual invocation.
- **Storage:** JSON file (`.docrot-fingerprints.json`). SQLite planned for post-MVP.
- **Output:** CI log warnings + `.docrot-report.json` artifact + GitHub commit statuses. PR comments planned for post-MVP.
- **Thresholds:** Global only. Per-module overrides planned for post-MVP.

## License

This project is for academic use as part of the CS 4485 Capstone course.
