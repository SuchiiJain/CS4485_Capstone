# Docrot Detector — System Architecture

## Layered Architecture

The project follows a **4-layer pipeline** architecture, where each layer feeds the next sequentially on every CI run or push event:

```
┌─────────────────────────────────────────────────────────────┐
│                      TRIGGER                                │
│  git push / CI run  ──►  on_push_or_ci_run(repo, old, new) │
└────────────────────────────┬────────────────────────────────┘
                             │
         ┌───────────────────▼───────────────────┐
         │  1. CHANGE DETECTION LAYER            │
         │  get_changed_python_files()           │
         │  ► git diff to find modified .py files│
         └───────────────────┬───────────────────┘
                             │  list of changed files
         ┌───────────────────▼───────────────────┐
         │  2. AST PARSING + FINGERPRINTING      │
         │  extract_function_fingerprints()      │
         │  ► parse AST                          │
         │  ► normalize (strip noise)            │
         │  ► build semantic fingerprint per fn  │
         │    ┌──────────────────────────┐       │
         │    │ Fingerprint features:    │       │
         │    │  signature               │       │
         │    │  control_flow            │       │
         │    │  conditions              │       │
         │    │  calls                   │       │
         │    │  side_effects            │       │
         │    │  exceptions              │       │
         │    │  returns                 │       │
         │    │  api_visibility          │       │
         │    └──────────────────────────┘       │
         └───────────────────┬───────────────────┘
                             │  per-function fingerprints
         ┌───────────────────▼───────────────────┐
         │  3. COMPARISON + SCORING LAYER        │
         │  compare_file_functions()             │
         │  ► diff old vs new fingerprints       │
         │  ► score_semantic_delta() per fn      │
         │  ► emit events: added/removed/changed │
         │                                       │
         │  Scoring weights:                     │
         │    0 pts  format/comment only          │
         │    1 pt   literal/default tweak        │
         │    3 pts  condition/loop/return change  │
         │    5 pts  public API signature change   │
         │    6 pts  side-effect/auth change       │
         │    8 pts  exception/control path change │
         └───────────────────┬───────────────────┘
                             │  scored function events
         ┌───────────────────▼───────────────────┐
         │  4. ALERT LAYER                       │
         │  evaluate_doc_flags()                 │
         │  ► map code paths → doc files (config)│
         │  ► per-fn threshold (≥4 or critical)  │
         │  ► per-doc cumulative threshold (≥8)  │
         │  publish_alerts()                     │
         │  ► CI log warnings                    │
         │  ► .docrot-report.json artifact       │
         └───────────────────────────────────────┘
```

## Cross-Cutting Concerns

### Persistence Layer

Sits alongside layers 2–3 as a shared service:

| Aspect | MVP | Post-MVP |
|---|---|---|
| Storage format | `.docrot-fingerprints.json` | SQLite |
| Role | Single source of truth for "old" baseline | + indexed queries, history |
| Flow | `load_fingerprints()` before compare → `persist_fingerprints()` after | Same contract, different backend |

### Mapping Layer

Configuration that bridges code to docs:

- JSON config file mapping `code_glob` patterns to documentation file paths
- Used by the Alert Layer to look up which docs are affected by which code changes

## Key Data Flow Objects

| Object | Produced by | Consumed by |
|---|---|---|
| `changed_files` (list of .py paths) | Change Detection | AST Parsing |
| `fingerprints` (per-function feature dict + hash) | AST Parsing | Comparison; Persistence |
| `function_events` (fn_id, code_path, event_type, score, critical, reasons) | Comparison | Alert Layer |
| `doc_alerts` (doc_path, cumulative_score, critical_found, reasons, functions) | Alert Layer | Output/CI |

## First-Run Baseline Guard

The system has an explicit first-run path: if no stored fingerprints exist, it generates the baseline, persists it, publishes a notice, and returns **zero alerts**. New/deleted file flagging only kicks in on subsequent runs.

## Module Mapping to Source

The current `src/` modules map to the architecture as follows:

| Module | Layer |
|---|---|
| `src/config.py` | Config / Mapping |
| `src/ast_parser.py` | AST Parsing + Fingerprinting |
| `src/fingerprint.py` | AST Parsing + Fingerprinting |
| `src/comparator.py` | Comparison + Scoring |
| `src/models.py` | Shared data structures (events, fingerprints) |
| `src/persistence.py` | Persistence (load/store fingerprints) |
| `src/alerts.py` | Alert Layer (evaluate + publish) |
| `database/schema.sql` | Post-MVP persistence (SQLite) |

## Design Principles

- **Pipeline architecture** — each stage transforms data and passes it forward, with the persistence layer as a side-channel for baseline state.
- **No re-parsing of old code** — the stored fingerprint file *is* the old state, keeping the system simple and the persistence layer as the single source of truth.
- **Semantic over textual** — AST-based fingerprinting ignores formatting/comment noise and focuses on behavioral changes.
- **Weighted scoring with critical triggers** — tunable thresholds let teams adjust sensitivity; critical events (API changes, side-effects, auth, exceptions) always flag regardless of score.
- **Python-first MVP** — single-language support keeps parser logic consistent; different languages would require different AST parsers and normalization rules.
